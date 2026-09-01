"""Pydantic schemas for forensic timeline reconstruction."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TimestampType(str, Enum):
    """Classification of what a timestamp represents on the evidence."""

    CREATED = "created"
    MODIFIED = "modified"
    ACCESSED = "accessed"
    DELETED = "deleted"
    VISITED = "visited"
    DOWNLOADED = "downloaded"
    UPLOADED = "uploaded"
    GENERATED = "generated"
    EXTRACTED = "extracted"
    UNKNOWN = "unknown"


class TimelineEventType(str, Enum):
    """Controlled forensic timeline event types.

    New forensic event kinds can be added here without breaking existing values.
    """

    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_ACCESSED = "file_accessed"

    BROWSER_VISIT = "browser_visit"
    BROWSER_DOWNLOAD = "browser_download"
    BROWSER_BOOKMARK = "browser_bookmark"
    BROWSER_SEARCH = "browser_search"

    METADATA_CREATED = "metadata_created"
    METADATA_MODIFIED = "metadata_modified"

    UNKNOWN = "unknown"


class TimelineStatus(str, Enum):
    """Outcome status for a timeline reconstruction operation."""

    SUCCESS = "success"
    PARTIAL = "partial"
    EMPTY = "empty"
    ERROR = "error"


class TimelineEvent(BaseModel):
    """Normalized forensic timeline event with provenance."""

    event_id: str
    timestamp: datetime
    timestamp_original: str
    timestamp_type: TimestampType
    event_type: TimelineEventType
    source: str
    source_file: str
    description: str
    artifact: str
    path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class TimelineFilter(BaseModel):
    """Filter criteria for timeline event collections.

    Filtering always returns a new collection and never mutates the source.
    """

    start_time: datetime | None = None
    end_time: datetime | None = None
    event_types: list[TimelineEventType] | None = None
    sources: list[str] | None = None
    keyword: str | None = None
    path_contains: str | None = None


class TimelineSummary(BaseModel):
    """Aggregate statistics for a reconstructed timeline."""

    total_events: int = Field(ge=0, default=0)
    events_by_type: dict[str, int] = Field(default_factory=dict)
    events_by_source: dict[str, int] = Field(default_factory=dict)
    earliest_event: datetime | None = None
    latest_event: datetime | None = None
    message: str = ""


class TimelineResult(BaseModel):
    """Structured result of a timeline reconstruction run."""

    status: TimelineStatus
    events: list[TimelineEvent] = Field(default_factory=list)
    summary: TimelineSummary
    source: str
    generated_at: datetime
    warnings: list[str] = Field(default_factory=list)
    message: str = ""
