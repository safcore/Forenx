"""Timestamp normalization for forensic timeline events.

Naive timestamp policy
----------------------
When a source provides a **naive** ``datetime`` (no ``tzinfo``), ForenX attaches
UTC via ``replace(tzinfo=timezone.utc)``. This matches the existing Phase 3
metadata extractors (DOCX / EXIF / PDF) and does **not** assert that the
originating clock was definitely UTC.

The assumption is recorded on the event:

- ``metadata["timezone_policy"] = "assumed_utc_naive"``
- confidence is reduced relative to timezone-aware source values

Aware timestamps keep their offset information by converting with
``astimezone(timezone.utc)``. The original representation is always preserved
in ``timestamp_original``.

ForenX never fabricates timestamps for missing values.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.schemas.timeline import TimelineEvent, TimelineEventType, TimestampType
from app.timeline.models import RawTimelineCandidate, make_event_id
from app.utils.exceptions import TimelineError
from app.utils.logger import get_logger

logger = get_logger(__name__)

CONFIDENCE_AWARE = 0.95
CONFIDENCE_NAIVE_ASSUMED_UTC = 0.70
CONFIDENCE_FLOOR = 0.1


def format_timestamp_original(value: datetime) -> str:
    """Serialize a datetime for provenance without discarding timezone info."""
    return value.isoformat()


def normalize_to_utc(
    value: datetime,
    *,
    allow_naive: bool = True,
) -> tuple[datetime, str, float, dict[str, Any]]:
    """Normalize a datetime into timezone-aware UTC.

    Args:
        value: Source datetime (aware or naive).
        allow_naive: When ``False``, naive values raise ``TimelineError``.

    Returns:
        Tuple of ``(utc_datetime, original_iso, confidence, policy_metadata)``.

    Raises:
        TimelineError: If ``value`` is invalid or naive when disallowed.
    """
    if not isinstance(value, datetime):
        raise TimelineError(
            f"Invalid timestamp type: expected datetime, got {type(value).__name__}"
        )

    original = format_timestamp_original(value)
    policy: dict[str, Any] = {}

    if value.tzinfo is None:
        if not allow_naive:
            raise TimelineError(
                "Naive timestamp rejected: source did not provide timezone information"
            )
        utc_value = value.replace(tzinfo=timezone.utc)
        policy["timezone_policy"] = "assumed_utc_naive"
        confidence = CONFIDENCE_NAIVE_ASSUMED_UTC
        logger.debug("Normalized naive timestamp with assumed UTC policy")
        return utc_value, original, confidence, policy

    utc_value = value.astimezone(timezone.utc)
    if value.utcoffset() is not None and value.utcoffset().total_seconds() == 0:
        policy["timezone_policy"] = "source_already_utc"
    else:
        policy["timezone_policy"] = "source_timezone_converted_to_utc"
    confidence = CONFIDENCE_AWARE
    return utc_value, original, confidence, policy


def normalize_candidate(candidate: RawTimelineCandidate) -> TimelineEvent | None:
    """Convert a raw candidate into a ``TimelineEvent``, or skip if no timestamp.

    Args:
        candidate: Intermediate event payload.

    Returns:
        Normalized ``TimelineEvent``, or ``None`` when timestamp is missing
        (ForenX never fabricates forensic timestamps).

    Raises:
        TimelineError: When the provided timestamp is unusable.
    """
    if candidate.raw_timestamp is None:
        logger.debug(
            "Skipping timeline candidate without timestamp artifact=%s source=%s",
            candidate.artifact,
            candidate.source,
        )
        return None

    try:
        utc_ts, original, tz_confidence, policy = normalize_to_utc(
            candidate.raw_timestamp
        )
    except TimelineError:
        raise
    except (OverflowError, ValueError, OSError) as exc:
        raise TimelineError(
            f"Invalid timestamp for artifact '{candidate.artifact}': {exc}"
        ) from exc

    confidence = max(
        CONFIDENCE_FLOOR,
        min(1.0, candidate.base_confidence * tz_confidence),
    )
    metadata = dict(candidate.metadata)
    metadata.update(policy)

    event_id = make_event_id(
        timestamp=utc_ts,
        event_type=candidate.event_type,
        source=candidate.source,
        source_file=candidate.source_file,
        artifact=candidate.artifact,
        path=candidate.path,
        description=candidate.description,
    )
    return TimelineEvent(
        event_id=event_id,
        timestamp=utc_ts,
        timestamp_original=original,
        timestamp_type=candidate.timestamp_type,
        event_type=candidate.event_type,
        source=candidate.source,
        source_file=candidate.source_file,
        description=candidate.description,
        artifact=candidate.artifact,
        path=candidate.path,
        metadata=metadata,
        confidence=round(confidence, 4),
    )


def normalize_candidates(
    candidates: list[RawTimelineCandidate],
) -> tuple[list[TimelineEvent], list[str]]:
    """Normalize many candidates, collecting per-item warnings.

    Invalid individual timestamps become warnings; missing timestamps are skipped.
    """
    events: list[TimelineEvent] = []
    warnings: list[str] = []
    for candidate in candidates:
        try:
            event = normalize_candidate(candidate)
        except TimelineError as exc:
            warning = (
                f"Skipped invalid timestamp for artifact '{candidate.artifact}' "
                f"({candidate.source}): {exc}"
            )
            warnings.append(warning)
            logger.warning(warning)
            continue
        if event is not None:
            events.append(event)
    return events, warnings
