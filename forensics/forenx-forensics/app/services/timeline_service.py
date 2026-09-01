"""Timeline service orchestration for the ForenX forensics engine.

Provides the public Phase 6 API for reconstructing forensic timelines from
filesystem timestamps, browser artifacts (via BrowserService), and embedded
metadata timestamps (via MetadataService).

Typical usage example:

    from app.services.timeline_service import TimelineService

    result = TimelineService().build_timeline("evidence/sample_case")
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from app.schemas.timeline import (
    TimelineEvent,
    TimelineEventType,
    TimelineFilter,
    TimelineResult,
    TimelineStatus,
    TimelineSummary,
)
from app.services.browser_service import BrowserService
from app.services.metadata_service import MetadataService
from app.timeline.dispatcher import (
    build_summary,
    collect_timeline_events,
    sort_timeline_events,
)
from app.timeline.models import sort_key
from app.utils.exceptions import EvidenceFileError, TimelineError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TimelineService:
    """High-level API for forensic timeline reconstruction.

    Designed for reuse by CLI tools, tests, and a future Django backend.
    """

    def __init__(
        self,
        *,
        browser_service: BrowserService | None = None,
        metadata_service: MetadataService | None = None,
    ) -> None:
        """Initialize the timeline service.

        Args:
            browser_service: Optional shared ``BrowserService``.
            metadata_service: Optional shared ``MetadataService``.
        """
        self._browser_service = browser_service or BrowserService()
        self._metadata_service = metadata_service or MetadataService()

    def build_timeline(
        self,
        evidence_path: str | Path,
        *,
        include_filesystem: bool = True,
        include_browser: bool = True,
        include_metadata: bool = True,
    ) -> TimelineResult:
        """Build a timeline from a file, browser profile, or evidence directory.

        Args:
            evidence_path: Evidence file or directory path.
            include_filesystem: Include filesystem created/modified/accessed events.
            include_browser: Include browser artifact events.
            include_metadata: Include embedded metadata timestamp events.

        Returns:
            Structured ``TimelineResult``.
        """
        logger.info(
            "TimelineService.build_timeline started path=%s",
            Path(evidence_path) if evidence_path else "",
        )
        result = collect_timeline_events(
            evidence_path,
            include_filesystem=include_filesystem,
            include_browser=include_browser,
            include_metadata=include_metadata,
            browser_service=self._browser_service,
            metadata_service=self._metadata_service,
        )
        logger.info(
            "TimelineService.build_timeline finished events=%d status=%s",
            result.summary.total_events,
            result.status.value,
        )
        return result

    def build_from_file(
        self,
        file_path: str | Path,
        *,
        include_filesystem: bool = True,
        include_metadata: bool = True,
    ) -> TimelineResult:
        """Build a timeline from a single evidence file (no browser discovery)."""
        path = Path(file_path)
        if not str(file_path).strip():
            raise EvidenceFileError("Timeline file path must not be empty")
        if not path.exists():
            raise EvidenceFileError(f"Evidence file not found: {path}")
        if not path.is_file():
            raise EvidenceFileError(f"Evidence path is not a file: {path}")
        return self.build_timeline(
            path,
            include_filesystem=include_filesystem,
            include_browser=False,
            include_metadata=include_metadata,
        )

    def build_from_directory(
        self,
        directory: str | Path,
        *,
        include_filesystem: bool = True,
        include_browser: bool = True,
        include_metadata: bool = True,
    ) -> TimelineResult:
        """Build a timeline from an evidence directory tree."""
        path = Path(directory)
        if not str(directory).strip():
            raise EvidenceFileError("Timeline directory path must not be empty")
        if not path.exists():
            raise EvidenceFileError(f"Evidence directory not found: {path}")
        if not path.is_dir():
            raise EvidenceFileError(f"Evidence path is not a directory: {path}")
        return self.build_timeline(
            path,
            include_filesystem=include_filesystem,
            include_browser=include_browser,
            include_metadata=include_metadata,
        )

    def filter_by_time_range(
        self,
        events: Sequence[TimelineEvent],
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[TimelineEvent]:
        """Return events within ``[start_time, end_time]`` (inclusive).

        Does not mutate the input collection.
        """
        if start_time is not None and end_time is not None and start_time > end_time:
            raise TimelineError("start_time must be less than or equal to end_time")

        filtered: list[TimelineEvent] = []
        for event in events:
            if start_time is not None and event.timestamp < start_time:
                continue
            if end_time is not None and event.timestamp > end_time:
                continue
            filtered.append(event)
        return filtered

    def filter_by_event_type(
        self,
        events: Sequence[TimelineEvent],
        event_types: Sequence[TimelineEventType | str],
    ) -> list[TimelineEvent]:
        """Return events whose type is in ``event_types``."""
        allowed: set[str] = set()
        for item in event_types:
            if isinstance(item, TimelineEventType):
                allowed.add(item.value)
            else:
                allowed.add(str(item))
        return [event for event in events if event.event_type.value in allowed]

    def filter_events(
        self,
        events: Sequence[TimelineEvent],
        timeline_filter: TimelineFilter,
    ) -> list[TimelineEvent]:
        """Apply a ``TimelineFilter`` without mutating the input collection."""
        result = list(events)
        if (
            timeline_filter.start_time is not None
            or timeline_filter.end_time is not None
        ):
            result = self.filter_by_time_range(
                result,
                start_time=timeline_filter.start_time,
                end_time=timeline_filter.end_time,
            )
        if timeline_filter.event_types:
            result = self.filter_by_event_type(result, timeline_filter.event_types)
        if timeline_filter.sources:
            allowed_sources = {source.lower() for source in timeline_filter.sources}
            result = [
                event
                for event in result
                if event.source.lower() in allowed_sources
                or any(
                    event.source.lower().startswith(f"{allowed}:")
                    for allowed in allowed_sources
                )
            ]
        if timeline_filter.keyword:
            needle = timeline_filter.keyword.lower()
            result = [
                event
                for event in result
                if needle in event.description.lower()
                or needle in (event.path or "").lower()
                or needle in event.artifact.lower()
            ]
        if timeline_filter.path_contains:
            fragment = timeline_filter.path_contains.lower()
            result = [
                event
                for event in result
                if fragment in (event.path or "").lower()
                or fragment in event.source_file.lower()
            ]
        return result

    def sort_events(self, events: Sequence[TimelineEvent]) -> list[TimelineEvent]:
        """Return events sorted chronologically with deterministic secondary keys."""
        return sort_timeline_events(list(events))

    def summarize(self, events: Sequence[TimelineEvent] | TimelineResult) -> TimelineSummary:
        """Build a human-readable statistical summary for events or a result."""
        if isinstance(events, TimelineResult):
            return build_summary(events.events, message=events.summary.message)
        ordered = sorted(events, key=sort_key)
        return build_summary(ordered)

    def empty_result(self, source: str = "") -> TimelineResult:
        """Return an empty timeline result (useful for hosts / tests)."""
        from datetime import timezone

        return TimelineResult(
            status=TimelineStatus.EMPTY,
            events=[],
            summary=build_summary([]),
            source=source,
            generated_at=datetime.now(timezone.utc),
            warnings=[],
            message="No timeline events extracted",
        )
