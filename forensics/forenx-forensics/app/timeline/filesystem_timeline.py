"""Filesystem timestamp extraction for forensic timelines."""

from __future__ import annotations

from pathlib import Path

from app.hashing.hash_generator import resolve_evidence_path
from app.schemas.timeline import TimelineEvent, TimelineEventType, TimestampType
from app.timeline.event_normalizer import normalize_candidates
from app.timeline.models import SOURCE_FILESYSTEM, RawTimelineCandidate
from app.utils.exceptions import EvidenceFileError, TimelineError
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _posix_to_datetime(timestamp: float | None):
    """Convert a POSIX timestamp using the project UTC policy."""
    if timestamp is None:
        return None
    from datetime import datetime, timezone

    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def extract_filesystem_events(file_path: str | Path) -> tuple[list[TimelineEvent], list[str]]:
    """Extract created / modified / accessed events for an evidence file.

    Uses ``Path.stat(follow_symlinks=False)`` so symlink targets are not followed
    during metadata collection. Evidence files are never modified.

    Args:
        file_path: Path to a regular evidence file.

    Returns:
        Tuple of ``(events, warnings)``.

    Raises:
        EvidenceFileError: If the path is empty, missing, or not a file.
        TimelineError: If filesystem timestamps cannot be collected.
    """
    path = resolve_evidence_path(file_path)
    logger.info("Filesystem timeline extraction started for '%s'", path.name)

    try:
        stats = path.stat(follow_symlinks=False)
    except PermissionError as exc:
        raise EvidenceFileError(
            f"Permission denied while reading filesystem timestamps: {path}"
        ) from exc
    except OSError as exc:
        raise TimelineError(
            f"Failed to stat evidence file for timeline '{path}': {exc}"
        ) from exc

    created = getattr(stats, "st_birthtime", None)
    if created is None:
        created = stats.st_ctime

    source_file = str(path.resolve(strict=False))
    candidates = [
        RawTimelineCandidate(
            raw_timestamp=_posix_to_datetime(created),
            timestamp_type=TimestampType.CREATED,
            event_type=TimelineEventType.FILE_CREATED,
            source=SOURCE_FILESYSTEM,
            source_file=source_file,
            description=f"Filesystem created/birth time for {path.name}",
            artifact="filesystem.created",
            path=source_file,
            metadata={"stat_field": "st_birthtime_or_st_ctime"},
            base_confidence=0.9,
        ),
        RawTimelineCandidate(
            raw_timestamp=_posix_to_datetime(stats.st_mtime),
            timestamp_type=TimestampType.MODIFIED,
            event_type=TimelineEventType.FILE_MODIFIED,
            source=SOURCE_FILESYSTEM,
            source_file=source_file,
            description=f"Filesystem modified time for {path.name}",
            artifact="filesystem.modified",
            path=source_file,
            metadata={"stat_field": "st_mtime"},
            base_confidence=0.95,
        ),
        RawTimelineCandidate(
            raw_timestamp=_posix_to_datetime(stats.st_atime),
            timestamp_type=TimestampType.ACCESSED,
            event_type=TimelineEventType.FILE_ACCESSED,
            source=SOURCE_FILESYSTEM,
            source_file=source_file,
            description=f"Filesystem accessed time for {path.name}",
            artifact="filesystem.accessed",
            path=source_file,
            metadata={"stat_field": "st_atime"},
            base_confidence=0.75,
        ),
    ]

    events, warnings = normalize_candidates(candidates)
    logger.info(
        "Filesystem timeline extraction finished for '%s' events=%d",
        path.name,
        len(events),
    )
    return events, warnings
