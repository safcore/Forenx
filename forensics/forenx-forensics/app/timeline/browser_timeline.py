"""Convert Phase 5 browser analysis results into timeline events.

Does not parse browser databases directly; callers must supply
``BrowserResult`` objects from ``BrowserService``.
"""

from __future__ import annotations

from typing import Any

from app.schemas.browser import (
    BrowserBookmark,
    BrowserDownload,
    BrowserResult,
    BrowserSearch,
    BrowserVisit,
)
from app.schemas.timeline import TimelineEvent, TimelineEventType, TimestampType
from app.timeline.event_normalizer import normalize_candidates
from app.timeline.models import RawTimelineCandidate, browser_source_label
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _base_meta(result: BrowserResult) -> dict[str, Any]:
    """Shared provenance metadata for events derived from one profile analysis."""
    return {
        "browser": result.browser,
        "profile_name": result.profile_name,
        "profile_path": result.profile_path,
    }


def _visit_candidates(
    result: BrowserResult,
    visits: list[BrowserVisit],
) -> list[RawTimelineCandidate]:
    source = browser_source_label(result.browser)
    source_file = result.profile_path
    base = _base_meta(result)
    out: list[RawTimelineCandidate] = []
    for visit in visits:
        meta = {
            **base,
            "url": visit.url,
            "title": visit.title,
            "visit_count": visit.visit_count,
            "domain": visit.domain,
            "transition_type": visit.transition_type,
        }
        out.append(
            RawTimelineCandidate(
                raw_timestamp=visit.visit_time,
                timestamp_type=TimestampType.VISITED,
                event_type=TimelineEventType.BROWSER_VISIT,
                source=source,
                source_file=source_file,
                description=f"Visited {visit.url}",
                artifact="browser.history",
                path=visit.url,
                metadata=meta,
                base_confidence=0.95,
            )
        )
    return out


def _download_candidates(
    result: BrowserResult,
    downloads: list[BrowserDownload],
) -> list[RawTimelineCandidate]:
    source = browser_source_label(result.browser)
    source_file = result.profile_path
    base = _base_meta(result)
    out: list[RawTimelineCandidate] = []
    for item in downloads:
        meta = {
            **base,
            "source_url": item.source_url,
            "local_path": item.local_path,
            "file_size": item.file_size,
            "danger_status": item.danger_status,
        }
        label = item.local_path or item.source_url or "download"
        out.append(
            RawTimelineCandidate(
                raw_timestamp=item.downloaded_time,
                timestamp_type=TimestampType.DOWNLOADED,
                event_type=TimelineEventType.BROWSER_DOWNLOAD,
                source=source,
                source_file=source_file,
                description=f"Downloaded {label}",
                artifact="browser.downloads",
                path=item.local_path or item.source_url,
                metadata=meta,
                base_confidence=0.95,
            )
        )
    return out


def _bookmark_candidates(
    result: BrowserResult,
    bookmarks: list[BrowserBookmark],
) -> list[RawTimelineCandidate]:
    source = browser_source_label(result.browser)
    source_file = result.profile_path
    base = _base_meta(result)
    out: list[RawTimelineCandidate] = []
    for item in bookmarks:
        meta = {
            **base,
            "url": item.url,
            "title": item.title,
            "folder": item.folder,
        }
        label = item.title or item.url or "bookmark"
        out.append(
            RawTimelineCandidate(
                raw_timestamp=item.created_time,
                timestamp_type=TimestampType.CREATED,
                event_type=TimelineEventType.BROWSER_BOOKMARK,
                source=source,
                source_file=source_file,
                description=f"Bookmarked {label}",
                artifact="browser.bookmarks",
                path=item.url,
                metadata=meta,
                base_confidence=0.9,
            )
        )
    return out


def _search_candidates(
    result: BrowserResult,
    searches: list[BrowserSearch],
) -> list[RawTimelineCandidate]:
    source = browser_source_label(result.browser)
    source_file = result.profile_path
    base = _base_meta(result)
    out: list[RawTimelineCandidate] = []
    for item in searches:
        meta = {
            **base,
            "engine": item.engine,
            "search_query": item.search_query,
            "url": item.url,
        }
        out.append(
            RawTimelineCandidate(
                raw_timestamp=item.visit_time,
                timestamp_type=TimestampType.VISITED,
                event_type=TimelineEventType.BROWSER_SEARCH,
                source=source,
                source_file=source_file,
                description=f"Search ({item.engine}): {item.search_query}",
                artifact="browser.searches",
                path=item.url,
                metadata=meta,
                base_confidence=0.9,
            )
        )
    return out


def extract_browser_events(
    result: BrowserResult,
) -> tuple[list[TimelineEvent], list[str]]:
    """Convert a ``BrowserResult`` into normalized timeline events.

    Cookie artifacts are intentionally excluded so cookie values (never present
    in Phase 5 schemas) cannot leak into timeline metadata.
    """
    logger.info(
        "Browser timeline conversion started browser=%s profile=%s",
        result.browser,
        result.profile_name,
    )
    candidates: list[RawTimelineCandidate] = []
    candidates.extend(_visit_candidates(result, result.history))
    candidates.extend(_download_candidates(result, result.downloads))
    candidates.extend(_bookmark_candidates(result, result.bookmarks))
    candidates.extend(_search_candidates(result, result.searches))

    events, warnings = normalize_candidates(candidates)
    logger.info(
        "Browser timeline conversion finished browser=%s events=%d",
        result.browser,
        len(events),
    )
    return events, warnings
