"""Timeline dispatcher: route evidence to extractors and combine events."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.browser.dispatcher import discover_profiles
from app.schemas.timeline import (
    TimelineEvent,
    TimelineResult,
    TimelineStatus,
    TimelineSummary,
)
from app.services.browser_service import BrowserService
from app.services.metadata_service import MetadataService
from app.timeline.browser_timeline import extract_browser_events
from app.timeline.filesystem_timeline import extract_filesystem_events
from app.timeline.metadata_timeline import extract_metadata_events
from app.timeline.models import DEFAULT_CORRELATION_WINDOW, sort_key
from app.timeline.parser import TimelineSourceKind, classify_evidence_path
from app.utils.exceptions import (
    BrowserHistoryError,
    EvidenceFileError,
    ForenXError,
    TimelineError,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def sort_timeline_events(events: list[TimelineEvent]) -> list[TimelineEvent]:
    """Return a new list sorted chronologically with deterministic secondary keys."""
    return sorted(events, key=sort_key)


def apply_soft_correlation(events: list[TimelineEvent]) -> list[TimelineEvent]:
    """Attach soft correlation hints without claiming definitive relationships.

    Hints are recorded under ``metadata['correlation_hints']`` as lists of
    related ``event_id`` values when:

    - events share the same absolute ``path`` / URL and fall within the
      correlation window, or
    - events share the same ``source_file`` and fall within the window.

    These are investigative hints only.
    """
    if len(events) < 2:
        return [event.model_copy(deep=True) for event in events]

    ordered = sort_timeline_events(events)
    cloned = [event.model_copy(deep=True) for event in ordered]

    for index, left in enumerate(cloned):
        related: set[str] = set(left.metadata.get("correlation_hints", []))
        for right in cloned[index + 1 :]:
            delta = right.timestamp - left.timestamp
            if delta > DEFAULT_CORRELATION_WINDOW:
                break
            same_path = (
                left.path
                and right.path
                and left.path == right.path
                and left.event_id != right.event_id
            )
            same_source_file = (
                left.source_file
                and left.source_file == right.source_file
                and left.event_id != right.event_id
            )
            if same_path or same_source_file:
                related.add(right.event_id)
                right_hints = set(right.metadata.get("correlation_hints", []))
                right_hints.add(left.event_id)
                right.metadata["correlation_hints"] = sorted(right_hints)
                right.metadata["correlation_note"] = (
                    "Possible temporal proximity; not a confirmed relationship"
                )
        if related:
            left.metadata["correlation_hints"] = sorted(related)
            left.metadata["correlation_note"] = (
                "Possible temporal proximity; not a confirmed relationship"
            )
    return cloned


def build_summary(events: list[TimelineEvent], *, message: str = "") -> TimelineSummary:
    """Compute aggregate statistics for a timeline event collection."""
    by_type: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for event in events:
        by_type[event.event_type.value] = by_type.get(event.event_type.value, 0) + 1
        by_source[event.source] = by_source.get(event.source, 0) + 1

    earliest = events[0].timestamp if events else None
    latest = events[-1].timestamp if events else None
    if not message:
        message = (
            f"Timeline contains {len(events)} event(s)"
            if events
            else "Timeline contains no events"
        )
    return TimelineSummary(
        total_events=len(events),
        events_by_type=dict(sorted(by_type.items())),
        events_by_source=dict(sorted(by_source.items())),
        earliest_event=earliest,
        latest_event=latest,
        message=message,
    )


def _status_for(events: list[TimelineEvent], warnings: list[str]) -> TimelineStatus:
    if not events and warnings:
        return TimelineStatus.PARTIAL
    if not events:
        return TimelineStatus.EMPTY
    if warnings:
        return TimelineStatus.PARTIAL
    return TimelineStatus.SUCCESS


def _finalize(
    events: list[TimelineEvent],
    warnings: list[str],
    *,
    source: str,
) -> TimelineResult:
    correlated = apply_soft_correlation(events)
    sorted_events = sort_timeline_events(correlated)
    status = _status_for(sorted_events, warnings)
    summary = build_summary(sorted_events)
    message = {
        TimelineStatus.SUCCESS: "Timeline reconstructed successfully",
        TimelineStatus.PARTIAL: "Timeline reconstructed with warnings or partial sources",
        TimelineStatus.EMPTY: "No timeline events extracted",
        TimelineStatus.ERROR: "Timeline reconstruction failed",
    }[status]
    return TimelineResult(
        status=status,
        events=sorted_events,
        summary=summary,
        source=source,
        generated_at=datetime.now(timezone.utc),
        warnings=list(warnings),
        message=message,
    )


def _extract_from_file(
    path: Path,
    *,
    include_filesystem: bool,
    include_metadata: bool,
    metadata_service: MetadataService,
) -> tuple[list[TimelineEvent], list[str]]:
    events: list[TimelineEvent] = []
    warnings: list[str] = []
    if include_filesystem:
        try:
            fs_events, fs_warnings = extract_filesystem_events(path)
            events.extend(fs_events)
            warnings.extend(fs_warnings)
        except ForenXError as exc:
            warning = f"Filesystem timeline failed for '{path.name}': {exc}"
            warnings.append(warning)
            logger.warning(warning)
    if include_metadata:
        meta_events, meta_warnings = extract_metadata_events(
            path,
            metadata_service=metadata_service,
        )
        events.extend(meta_events)
        warnings.extend(meta_warnings)
    return events, warnings


def _extract_from_browser_profile(
    path: Path,
    *,
    browser_service: BrowserService,
) -> tuple[list[TimelineEvent], list[str]]:
    warnings: list[str] = []
    try:
        result = browser_service.analyze_browser(path)
    except (BrowserHistoryError, EvidenceFileError, ForenXError) as exc:
        warning = f"Browser timeline failed for '{path}': {exc}"
        warnings.append(warning)
        logger.warning(warning)
        return [], warnings
    return extract_browser_events(result)


def _iter_regular_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for candidate in sorted(root.rglob("*")):
        if candidate.is_file():
            # Skip SQLite / Chromium lock-like internals under browser profiles;
            # browser databases are handled via BrowserService, not filesystem+metadata.
            name = candidate.name.lower()
            if name in {"history", "cookies", "places.sqlite", "favicons", "web data"}:
                continue
            if name.endswith(("-journal", "-wal", "-shm")):
                continue
            files.append(candidate)
    return files


def collect_timeline_events(
    evidence_path: str | Path,
    *,
    include_filesystem: bool = True,
    include_browser: bool = True,
    include_metadata: bool = True,
    browser_service: BrowserService | None = None,
    metadata_service: MetadataService | None = None,
) -> TimelineResult:
    """Dispatch evidence to extractors, normalize, correlate, and summarize.

    Raises:
        EvidenceFileError: When the evidence path is empty or missing.
        TimelineError: When reconstruction cannot proceed at all.
    """
    if evidence_path is None or (
        isinstance(evidence_path, str) and not str(evidence_path).strip()
    ):
        raise EvidenceFileError("Timeline evidence path must not be empty")

    path = Path(evidence_path)
    kind = classify_evidence_path(path)
    if kind is TimelineSourceKind.MISSING:
        raise EvidenceFileError(f"Evidence path not found: {path}")

    logger.info(
        "Timeline dispatch started path=%s kind=%s fs=%s browser=%s metadata=%s",
        path,
        kind.value,
        include_filesystem,
        include_browser,
        include_metadata,
    )

    browser_svc = browser_service or BrowserService()
    metadata_svc = metadata_service or MetadataService()
    events: list[TimelineEvent] = []
    warnings: list[str] = []
    source_label = str(path.resolve(strict=False))

    try:
        if kind is TimelineSourceKind.FILE:
            file_events, file_warnings = _extract_from_file(
                path,
                include_filesystem=include_filesystem,
                include_metadata=include_metadata,
                metadata_service=metadata_svc,
            )
            events.extend(file_events)
            warnings.extend(file_warnings)

        elif kind is TimelineSourceKind.BROWSER_PROFILE:
            if include_browser:
                browser_events, browser_warnings = _extract_from_browser_profile(
                    path,
                    browser_service=browser_svc,
                )
                events.extend(browser_events)
                warnings.extend(browser_warnings)
            else:
                warnings.append("Browser extraction disabled by caller flags")

        elif kind is TimelineSourceKind.DIRECTORY:
            browser_profile_paths: set[Path] = set()
            if include_browser:
                try:
                    profiles = discover_profiles(path)
                except EvidenceFileError as exc:
                    warnings.append(f"Browser profile discovery failed: {exc}")
                    profiles = []
                for profile_path, _browser in profiles:
                    browser_profile_paths.add(profile_path.resolve(strict=False))
                    logger.info("Source discovered: browser profile %s", profile_path)
                    browser_events, browser_warnings = _extract_from_browser_profile(
                        profile_path,
                        browser_service=browser_svc,
                    )
                    events.extend(browser_events)
                    warnings.extend(browser_warnings)

            if include_filesystem or include_metadata:
                for file_path in _iter_regular_files(path):
                    # Avoid double-counting files inside analyzed browser profiles
                    # for filesystem/metadata when they are binary DB internals.
                    if any(
                        profile in file_path.parents or profile == file_path.parent
                        for profile in browser_profile_paths
                    ):
                        # Still allow non-DB bookmarks JSON etc? Bookmarks is JSON -
                        # currently skipped by name check for History/Cookies only.
                        # Bookmarks file can contribute filesystem timestamps.
                        pass
                    file_events, file_warnings = _extract_from_file(
                        file_path,
                        include_filesystem=include_filesystem,
                        include_metadata=include_metadata,
                        metadata_service=metadata_svc,
                    )
                    events.extend(file_events)
                    warnings.extend(file_warnings)
        else:
            raise TimelineError(f"Unsupported evidence kind for timeline: {kind}")
    except EvidenceFileError:
        raise
    except TimelineError:
        raise
    except ForenXError as exc:
        raise TimelineError(f"Timeline reconstruction failed: {exc}") from exc

    result = _finalize(events, warnings, source=source_label)
    logger.info(
        "Timeline dispatch finished source=%s events=%d status=%s warnings=%d",
        source_label,
        result.summary.total_events,
        result.status.value,
        len(result.warnings),
    )
    return result
