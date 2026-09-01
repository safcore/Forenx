"""Tests for Phase 6 timeline reconstruction."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.browser import (
    BrowserBookmark,
    BrowserDownload,
    BrowserResult,
    BrowserSearch,
    BrowserStatus,
    BrowserSummary,
    BrowserVisit,
)
from app.schemas.metadata import DocumentMetadata, ImageMetadata, MetadataStatus, PdfMetadata
from app.schemas.timeline import (
    TimelineEvent,
    TimelineEventType,
    TimelineFilter,
    TimelineStatus,
    TimestampType,
)
from app.services.timeline_service import TimelineService
from app.timeline.browser_timeline import extract_browser_events
from app.timeline.event_normalizer import normalize_candidate, normalize_to_utc
from app.timeline.filesystem_timeline import extract_filesystem_events
from app.timeline.metadata_timeline import (
    extract_metadata_events,
    extract_metadata_events_from_result,
)
from app.timeline.models import RawTimelineCandidate
from app.utils.exceptions import EvidenceFileError, TimelineError
from tests.browser_fixtures import build_chromium_profile


@pytest.fixture
def sample_text(tmp_path: Path) -> Path:
    """Create a small text evidence file."""
    path = tmp_path / "timeline_note.txt"
    path.write_text("Synthetic ForenX timeline evidence note.\n", encoding="utf-8")
    return path


def _empty_browser_summary(**kwargs) -> BrowserSummary:
    defaults = {
        "browser": "chrome",
        "profile_name": "Default",
        "timestamp": datetime.now(timezone.utc),
        "status": BrowserStatus.SUCCESS,
        "message": "ok",
    }
    defaults.update(kwargs)
    return BrowserSummary(**defaults)


def _browser_result(**kwargs) -> BrowserResult:
    now = datetime.now(timezone.utc)
    defaults = {
        "browser": "chrome",
        "profile_name": "Default",
        "profile_path": "/tmp/chrome/Default",
        "status": BrowserStatus.SUCCESS,
        "message": "ok",
        "timestamp": now,
        "execution_time_ms": 1.0,
        "history": [],
        "downloads": [],
        "bookmarks": [],
        "cookies": [],
        "searches": [],
        "login_pages": [],
        "summary": _empty_browser_summary(),
    }
    defaults.update(kwargs)
    if "summary" not in kwargs:
        defaults["summary"] = _empty_browser_summary(
            browser=defaults["browser"],
            profile_name=defaults["profile_name"],
            history_count=len(defaults["history"]),
            download_count=len(defaults["downloads"]),
            bookmark_count=len(defaults["bookmarks"]),
            search_count=len(defaults["searches"]),
        )
    return BrowserResult(**defaults)


class TestFilesystemTimeline:
    def test_filesystem_created_timestamp(
        self, timeline_service: TimelineService, sample_text: Path
    ) -> None:
        result = timeline_service.build_from_file(sample_text, include_metadata=False)
        created = [
            e for e in result.events if e.event_type is TimelineEventType.FILE_CREATED
        ]
        assert created
        assert created[0].timestamp_type is TimestampType.CREATED
        assert created[0].timestamp.tzinfo is not None

    def test_filesystem_modified_timestamp(self, sample_text: Path) -> None:
        events, _ = extract_filesystem_events(sample_text)
        modified = [
            e for e in events if e.event_type is TimelineEventType.FILE_MODIFIED
        ]
        assert modified
        assert modified[0].timestamp_type is TimestampType.MODIFIED

    def test_filesystem_accessed_timestamp(self, sample_text: Path) -> None:
        events, _ = extract_filesystem_events(sample_text)
        accessed = [
            e for e in events if e.event_type is TimelineEventType.FILE_ACCESSED
        ]
        assert accessed
        assert accessed[0].timestamp_type is TimestampType.ACCESSED


class TestBrowserTimelineConversion:
    def test_browser_visit_conversion(self) -> None:
        visit_time = datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc)
        result = _browser_result(
            history=[
                BrowserVisit(
                    browser="chrome",
                    url="https://example.com",
                    title="Example",
                    visit_time=visit_time,
                )
            ]
        )
        events, _ = extract_browser_events(result)
        assert len(events) == 1
        assert events[0].event_type is TimelineEventType.BROWSER_VISIT
        assert events[0].timestamp == visit_time
        assert events[0].source == "browser:chrome"
        assert events[0].metadata.get("url") == "https://example.com"

    def test_browser_download_conversion(self) -> None:
        downloaded = datetime(2024, 6, 15, 13, 0, tzinfo=timezone.utc)
        result = _browser_result(
            downloads=[
                BrowserDownload(
                    browser="chrome",
                    source_url="https://files.example/report.pdf",
                    local_path=r"C:\Downloads\report.pdf",
                    downloaded_time=downloaded,
                )
            ]
        )
        events, _ = extract_browser_events(result)
        assert events[0].event_type is TimelineEventType.BROWSER_DOWNLOAD
        assert events[0].timestamp_type is TimestampType.DOWNLOADED

    def test_browser_search_conversion(self) -> None:
        visit_time = datetime(2024, 6, 15, 14, 0, tzinfo=timezone.utc)
        result = _browser_result(
            searches=[
                BrowserSearch(
                    browser="chrome",
                    engine="google",
                    search_query="forensics timeline",
                    visit_time=visit_time,
                    url="https://www.google.com/search?q=forensics",
                )
            ]
        )
        events, _ = extract_browser_events(result)
        assert events[0].event_type is TimelineEventType.BROWSER_SEARCH
        assert "forensics timeline" in events[0].description

    def test_browser_bookmark_conversion(self) -> None:
        created = datetime(2024, 6, 15, 15, 0, tzinfo=timezone.utc)
        result = _browser_result(
            bookmarks=[
                BrowserBookmark(
                    browser="chrome",
                    title="Docs",
                    url="https://docs.example",
                    created_time=created,
                    folder="Work",
                )
            ]
        )
        events, _ = extract_browser_events(result)
        assert events[0].event_type is TimelineEventType.BROWSER_BOOKMARK

    def test_no_cookie_values_exposed(self) -> None:
        result = _browser_result(
            history=[
                BrowserVisit(
                    browser="chrome",
                    url="https://example.com",
                    visit_time=datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc),
                )
            ]
        )
        # Even if callers stuffed cookie-like values into metadata, Phase 6
        # conversion never reads cookies from BrowserResult.cookies.
        events, _ = extract_browser_events(result)
        serialized = " ".join(str(event.metadata) for event in events)
        assert "cookie_value" not in serialized.lower()
        assert "cookies" not in {event.artifact for event in events}


class TestMetadataTimeline:
    def test_metadata_timestamp_conversion(self, tmp_path: Path) -> None:
        path = tmp_path / "doc.bin"
        path.write_bytes(b"placeholder")
        from app.schemas.metadata import MetadataResult

        created = datetime(2023, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        modified = datetime(2023, 2, 3, 4, 5, 6, tzinfo=timezone.utc)
        result = MetadataResult(
            timestamp=datetime.now(timezone.utc),
            status=MetadataStatus.SUCCESS,
            message="ok",
            file_type="docx",
            file_name=path.name,
            document=DocumentMetadata(
                timestamp=datetime.now(timezone.utc),
                status=MetadataStatus.SUCCESS,
                message="ok",
                file_name=path.name,
                created_date=created,
                modified_date=modified,
            ),
        )
        events, _ = extract_metadata_events_from_result(path, result)
        types = {event.event_type for event in events}
        assert TimelineEventType.METADATA_CREATED in types
        assert TimelineEventType.METADATA_MODIFIED in types
        assert all(event.source.startswith("metadata:") for event in events)

    def test_metadata_skips_missing_timestamps(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.png"
        path.write_bytes(b"x")
        from app.schemas.metadata import MetadataResult

        result = MetadataResult(
            timestamp=datetime.now(timezone.utc),
            status=MetadataStatus.PARTIAL,
            message="ok",
            file_type="image",
            file_name=path.name,
            image=ImageMetadata(
                timestamp=datetime.now(timezone.utc),
                status=MetadataStatus.PARTIAL,
                message="ok",
                filename=path.name,
                extension=".png",
                file_size=1,
                date_taken=None,
            ),
        )
        events, _ = extract_metadata_events_from_result(path, result)
        assert events == []


class TestTimestampNormalization:
    def test_timezone_aware_timestamps(self) -> None:
        aware = datetime(2024, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
        utc_value, original, confidence, policy = normalize_to_utc(aware)
        assert utc_value.tzinfo is not None
        assert utc_value == aware.astimezone(timezone.utc)
        assert "+05:30" in original or "+0530" in original.replace(":", "")
        assert confidence >= 0.9
        assert policy["timezone_policy"] == "source_timezone_converted_to_utc"

    def test_naive_timestamp_handling(self) -> None:
        naive = datetime(2024, 1, 1, 12, 0, 0)
        utc_value, original, confidence, policy = normalize_to_utc(naive)
        assert utc_value.tzinfo is timezone.utc
        assert utc_value.replace(tzinfo=None) == naive
        assert "assumed_utc_naive" in policy["timezone_policy"]
        assert confidence < 0.9
        assert "T12:00:00" in original

    def test_invalid_timestamp_handling(self) -> None:
        with pytest.raises(TimelineError):
            normalize_to_utc("not-a-datetime")  # type: ignore[arg-type]

        candidate = RawTimelineCandidate(
            raw_timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            timestamp_type=TimestampType.UNKNOWN,
            event_type=TimelineEventType.UNKNOWN,
            source="test",
            source_file="x",
            description="d",
            artifact="a",
        )
        # Corrupt after construction via invalid type path
        candidate.raw_timestamp = object()  # type: ignore[assignment]
        with pytest.raises(TimelineError):
            normalize_candidate(candidate)


class TestSortingAndFiltering:
    def _events(self) -> list[TimelineEvent]:
        base = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        items = []
        for index, (offset, etype, source) in enumerate(
            [
                (2, TimelineEventType.BROWSER_VISIT, "browser:chrome"),
                (0, TimelineEventType.FILE_CREATED, "filesystem"),
                (1, TimelineEventType.FILE_MODIFIED, "filesystem"),
                (1, TimelineEventType.BROWSER_SEARCH, "browser:chrome"),
            ]
        ):
            ts = base + timedelta(hours=offset)
            items.append(
                TimelineEvent(
                    event_id=f"e{index}",
                    timestamp=ts,
                    timestamp_original=ts.isoformat(),
                    timestamp_type=TimestampType.UNKNOWN,
                    event_type=etype,
                    source=source,
                    source_file=f"src-{index}",
                    description=f"event {index}",
                    artifact=f"artifact-{index}",
                    path=f"/path/{index}",
                    metadata={},
                    confidence=1.0,
                )
            )
        return items

    def test_chronological_sorting(self, timeline_service: TimelineService) -> None:
        sorted_events = timeline_service.sort_events(self._events())
        timestamps = [event.timestamp for event in sorted_events]
        assert timestamps == sorted(timestamps)

    def test_deterministic_sorting(self, timeline_service: TimelineService) -> None:
        events = self._events()
        first = [e.event_id for e in timeline_service.sort_events(events)]
        second = [e.event_id for e in timeline_service.sort_events(list(reversed(events)))]
        assert first == second

    def test_start_time_filtering(self, timeline_service: TimelineService) -> None:
        events = self._events()
        start = datetime(2024, 6, 1, 13, 0, tzinfo=timezone.utc)
        filtered = timeline_service.filter_by_time_range(events, start_time=start)
        assert all(event.timestamp >= start for event in filtered)
        assert len(filtered) < len(events)

    def test_end_time_filtering(self, timeline_service: TimelineService) -> None:
        events = self._events()
        end = datetime(2024, 6, 1, 13, 0, tzinfo=timezone.utc)
        filtered = timeline_service.filter_by_time_range(events, end_time=end)
        assert all(event.timestamp <= end for event in filtered)

    def test_event_type_filtering(self, timeline_service: TimelineService) -> None:
        events = self._events()
        filtered = timeline_service.filter_by_event_type(
            events, [TimelineEventType.FILE_CREATED]
        )
        assert filtered
        assert all(e.event_type is TimelineEventType.FILE_CREATED for e in filtered)

    def test_source_filtering(self, timeline_service: TimelineService) -> None:
        events = self._events()
        filtered = timeline_service.filter_events(
            events,
            TimelineFilter(sources=["filesystem"]),
        )
        assert filtered
        assert all(e.source == "filesystem" for e in filtered)
        browser_filtered = timeline_service.filter_events(
            events,
            TimelineFilter(sources=["browser"]),
        )
        assert browser_filtered
        assert all(e.source.startswith("browser:") for e in browser_filtered)


class TestTimelineServiceOrchestration:
    def test_directory_timeline(
        self, timeline_service: TimelineService, tmp_path: Path
    ) -> None:
        note = tmp_path / "case"
        note.mkdir()
        (note / "note.txt").write_text("hello", encoding="utf-8")
        build_chromium_profile(note / "chrome" / "Default")
        result = timeline_service.build_from_directory(note)
        assert result.status in {TimelineStatus.SUCCESS, TimelineStatus.PARTIAL}
        assert result.summary.total_events > 0
        types = {event.event_type for event in result.events}
        assert TimelineEventType.FILE_CREATED in types
        assert TimelineEventType.BROWSER_VISIT in types

    def test_missing_evidence(self, timeline_service: TimelineService) -> None:
        with pytest.raises(EvidenceFileError):
            timeline_service.build_timeline("does/not/exist-evidence")

    def test_corrupt_unsupported_source(
        self, timeline_service: TimelineService, tmp_path: Path
    ) -> None:
        bad_profile = tmp_path / "bad_profile"
        bad_profile.mkdir()
        (bad_profile / "History").write_bytes(b"not-a-sqlite-database")
        result = timeline_service.build_timeline(bad_profile)
        assert result.warnings
        assert result.status in {
            TimelineStatus.PARTIAL,
            TimelineStatus.EMPTY,
            TimelineStatus.SUCCESS,
        }

    def test_empty_timeline(self, timeline_service: TimelineService) -> None:
        empty = timeline_service.empty_result(source="none")
        assert empty.status is TimelineStatus.EMPTY
        assert empty.events == []
        assert empty.summary.total_events == 0

    def test_timeline_summary(
        self, timeline_service: TimelineService, sample_text: Path
    ) -> None:
        result = timeline_service.build_from_file(sample_text, include_metadata=False)
        summary = timeline_service.summarize(result)
        assert summary.total_events == len(result.events)
        assert summary.earliest_event is not None
        assert summary.latest_event is not None
        assert summary.events_by_type
        assert summary.events_by_source.get("filesystem", 0) > 0

    def test_provenance_preservation(
        self, timeline_service: TimelineService, sample_text: Path
    ) -> None:
        result = timeline_service.build_from_file(sample_text, include_metadata=False)
        for event in result.events:
            assert event.source
            assert event.source_file
            assert event.artifact
            assert event.timestamp_original

    def test_service_orchestration_with_flags(
        self, timeline_service: TimelineService, chrome_profile: Path
    ) -> None:
        result = timeline_service.build_timeline(
            chrome_profile,
            include_filesystem=False,
            include_browser=True,
            include_metadata=False,
        )
        assert any(
            event.event_type is TimelineEventType.BROWSER_VISIT for event in result.events
        )
        assert all(not event.source.startswith("filesystem") for event in result.events)

    def test_unsupported_metadata_file_does_not_fail(
        self, timeline_service: TimelineService, sample_text: Path
    ) -> None:
        events, warnings = extract_metadata_events(sample_text)
        assert events == []
        # Unsupported type is soft-skipped, not a hard failure.
        assert warnings == [] or all(isinstance(item, str) for item in warnings)

    def test_filter_does_not_mutate_original(
        self, timeline_service: TimelineService
    ) -> None:
        events = [
            TimelineEvent(
                event_id="a",
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
                timestamp_original="2024-01-01T00:00:00+00:00",
                timestamp_type=TimestampType.CREATED,
                event_type=TimelineEventType.FILE_CREATED,
                source="filesystem",
                source_file="/a",
                description="a",
                artifact="filesystem.created",
                confidence=1.0,
            ),
            TimelineEvent(
                event_id="b",
                timestamp=datetime(2024, 2, 1, tzinfo=timezone.utc),
                timestamp_original="2024-02-01T00:00:00+00:00",
                timestamp_type=TimestampType.MODIFIED,
                event_type=TimelineEventType.FILE_MODIFIED,
                source="filesystem",
                source_file="/b",
                description="b",
                artifact="filesystem.modified",
                confidence=1.0,
            ),
        ]
        original_len = len(events)
        filtered = timeline_service.filter_by_event_type(
            events, [TimelineEventType.FILE_CREATED]
        )
        assert len(events) == original_len
        assert len(filtered) == 1

    def test_confidence_bounds(self) -> None:
        with pytest.raises(ValidationError):
            TimelineEvent(
                event_id="x",
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
                timestamp_original="x",
                timestamp_type=TimestampType.UNKNOWN,
                event_type=TimelineEventType.UNKNOWN,
                source="s",
                source_file="f",
                description="d",
                artifact="a",
                confidence=1.5,
            )
