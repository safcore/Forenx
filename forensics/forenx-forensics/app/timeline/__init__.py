"""
Timeline reconstruction module (Phase 6).

Supported sources:
- filesystem timestamps (created / modified / accessed)
- browser artifacts via BrowserService (visits, downloads, bookmarks, searches)
- embedded metadata timestamps via MetadataService (image / PDF / DOCX)

Public orchestration lives in ``app.services.timeline_service.TimelineService``.
"""

from app.timeline.dispatcher import collect_timeline_events, sort_timeline_events
from app.timeline.event_normalizer import normalize_to_utc

__all__ = [
    "collect_timeline_events",
    "normalize_to_utc",
    "sort_timeline_events",
]
