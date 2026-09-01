"""Internal helpers and constants for timeline reconstruction."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from app.schemas.timeline import (
    TimelineEvent,
    TimelineEventType,
    TimestampType,
)

# Stable namespace so event IDs remain deterministic across process runs.
TIMELINE_EVENT_NAMESPACE = uuid.UUID("6f0e8d2a-4b91-4c3e-9f11-2a7d5e8c1b40")

# Default window for soft correlation hints (not definitive linkage).
DEFAULT_CORRELATION_WINDOW = timedelta(minutes=5)

SOURCE_FILESYSTEM = "filesystem"
SOURCE_BROWSER_PREFIX = "browser"
SOURCE_METADATA_PREFIX = "metadata"


@dataclass(slots=True)
class RawTimelineCandidate:
    """Unvalidated intermediate event before normalization into ``TimelineEvent``."""

    raw_timestamp: datetime | None
    timestamp_type: TimestampType
    event_type: TimelineEventType
    source: str
    source_file: str
    description: str
    artifact: str
    path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    base_confidence: float = 1.0


def make_event_id(
    *,
    timestamp: datetime,
    event_type: TimelineEventType,
    source: str,
    source_file: str,
    artifact: str,
    path: str | None,
    description: str,
) -> str:
    """Build a deterministic UUID5 event identifier."""
    path_part = path or ""
    payload = "|".join(
        [
            timestamp.isoformat(),
            event_type.value,
            source,
            source_file,
            artifact,
            path_part,
            description,
        ]
    )
    return str(uuid.uuid5(TIMELINE_EVENT_NAMESPACE, payload))


def browser_source_label(browser: str) -> str:
    """Return a provenance label such as ``browser:chrome``."""
    return f"{SOURCE_BROWSER_PREFIX}:{browser.strip().lower()}"


def metadata_source_label(kind: str) -> str:
    """Return a provenance label such as ``metadata:pdf``."""
    return f"{SOURCE_METADATA_PREFIX}:{kind.strip().lower()}"


def sort_key(event: TimelineEvent) -> tuple:
    """Stable chronological sort key for timeline events."""
    return (
        event.timestamp,
        event.event_type.value,
        event.source,
        event.source_file,
        event.artifact,
        event.event_id,
    )
