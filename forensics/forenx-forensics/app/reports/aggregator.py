"""Aggregate existing forensic service results into report sections.

Does not re-run Phase 2–7 analysis. Cookie values / secrets are sanitized.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.reports.models import sanitize_value
from app.schemas.browser import BrowserResult
from app.schemas.custody import CustodyEvent, CustodyVerificationResult
from app.schemas.hash import HashResult, HashVerificationResult, IntegrityResult
from app.schemas.keyword import KeywordResult, SearchResult
from app.schemas.metadata import MetadataResult
from app.schemas.report import (
    BrowserReportSection,
    CustodyReportSection,
    HashReportSection,
    KeywordReportSection,
    MetadataReportSection,
    TimelineReportSection,
)
from app.schemas.timeline import TimelineResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _dump(model: Any) -> dict[str, Any]:
    data = model.model_dump(mode="json")
    return sanitize_value(data)


def aggregate_hash_section(
    *,
    hash_results: Sequence[HashResult] | None = None,
    verification: HashVerificationResult | None = None,
    integrity: IntegrityResult | None = None,
    evidence_path: str | None = None,
) -> HashReportSection | None:
    """Build a hash/integrity report section from Phase 2 outputs."""
    if hash_results is None and verification is None and integrity is None:
        return None

    algorithms: dict[str, str] = {}
    path = evidence_path
    if hash_results:
        for item in hash_results:
            algorithms[item.algorithm.lower()] = item.hash
            path = path or item.file_name
    primary = algorithms.get("sha256")
    if integrity is not None:
        primary = primary or integrity.hash
        path = path or integrity.file_name
    if verification is not None:
        primary = primary or verification.hash
        path = path or verification.file_name

    limitations: list[str] = []
    if primary is None:
        limitations.append("SHA-256 digest unavailable in supplied hash results")

    message = "Hash and integrity results included"
    if integrity is not None:
        message = f"Integrity status={integrity.status.value}"
    logger.info("Aggregated hash report section algorithms=%d", len(algorithms))
    return HashReportSection(
        available=True,
        evidence_path=path,
        algorithms=dict(sorted(algorithms.items())),
        primary_sha256=primary,
        verification_verified=None if verification is None else verification.verified,
        integrity_status=None if integrity is None else integrity.status.value,
        integrity_verified=None if integrity is None else integrity.verified,
        message=message,
        provenance={
            "service": "HashService",
            "phase": 2,
            "note": "Values are evidence file digests, not custody event hashes",
        },
        limitations=limitations,
    )


def aggregate_metadata_section(
    metadata: MetadataResult | None,
) -> MetadataReportSection | None:
    """Build a metadata report section from Phase 3 output."""
    if metadata is None:
        return None
    limitations: list[str] = []
    if metadata.filesystem is None:
        limitations.append("Filesystem metadata unavailable")
    data = _dump(metadata)
    logger.info("Aggregated metadata report section file_type=%s", metadata.file_type)
    return MetadataReportSection(
        available=True,
        file_type=metadata.file_type,
        filesystem=data.get("filesystem"),
        image=data.get("image"),
        pdf=data.get("pdf"),
        document=data.get("document"),
        message=metadata.message,
        provenance={"service": "MetadataService", "phase": 3},
        limitations=limitations,
    )


def aggregate_keyword_section(
    search: SearchResult | KeywordResult | None,
    *,
    max_matches: int = 100,
) -> KeywordReportSection | None:
    """Build a keyword report section from Phase 4 output."""
    if search is None:
        return None

    if isinstance(search, SearchResult):
        summary = search.summary
        results = search.results
        keywords: list[str] = []
        for item in results:
            keywords.extend(item.keywords)
        searched = sorted({k for k in keywords if k})
        matches: list[dict[str, Any]] = []
        matched_files: list[str] = []
        for item in results:
            if item.match_count:
                matched_files.append(item.file_name)
            for match in item.matches[: max(0, max_matches - len(matches))]:
                matches.append(sanitize_value(match.model_dump(mode="json")))
            if len(matches) >= max_matches:
                break
        limitations: list[str] = []
        total_raw = summary.total_matches
        if total_raw > len(matches):
            limitations.append(
                f"Match list truncated to {len(matches)} of {total_raw} matches"
            )
        section = KeywordReportSection(
            available=True,
            searched_keywords=searched,
            total_files_searched=summary.total_files_searched,
            total_matches=summary.total_matches,
            files_with_matches=summary.files_with_matches,
            keyword_frequency=dict(sorted(summary.keyword_frequency.items())),
            matched_files=sorted(set(matched_files)),
            matches=matches,
            message=search.message,
            provenance={"service": "KeywordSearchService", "phase": 4},
            limitations=limitations,
        )
    else:
        matches = [
            sanitize_value(match.model_dump(mode="json"))
            for match in search.matches[:max_matches]
        ]
        limitations = []
        if search.match_count > len(matches):
            limitations.append(
                f"Match list truncated to {len(matches)} of {search.match_count}"
            )
        section = KeywordReportSection(
            available=True,
            searched_keywords=list(search.keywords),
            total_files_searched=1,
            total_matches=search.match_count,
            files_with_matches=1 if search.match_count else 0,
            keyword_frequency={
                key: sum(1 for match in search.matches if match.keyword == key)
                for key in search.keywords
            },
            matched_files=[search.file_name] if search.match_count else [],
            matches=matches,
            message=search.message,
            provenance={"service": "KeywordSearchService", "phase": 4},
            limitations=limitations,
        )
    logger.info(
        "Aggregated keyword report section matches=%d",
        section.total_matches,
    )
    return section


def aggregate_browser_section(
    browser: BrowserResult | Sequence[BrowserResult] | None,
) -> BrowserReportSection | None:
    """Build a browser report section from Phase 5 output."""
    if browser is None:
        return None
    items: list[BrowserResult]
    if isinstance(browser, BrowserResult):
        items = [browser]
    else:
        items = list(browser)

    profiles: list[dict[str, Any]] = []
    history = downloads = bookmarks = searches = logins = cookies = 0
    limitations: list[str] = []
    for item in items:
        history += item.summary.history_count
        downloads += item.summary.download_count
        bookmarks += item.summary.bookmark_count
        searches += item.summary.search_count
        logins += item.summary.login_page_count
        cookies += item.summary.cookie_count
        # Cookie metadata only — never values (Phase 5 schema has no values).
        cookie_meta = [
            sanitize_value(cookie.model_dump(mode="json")) for cookie in item.cookies
        ]
        profiles.append(
            sanitize_value(
                {
                    "browser": item.browser,
                    "profile_name": item.profile_name,
                    "profile_path": item.profile_path,
                    "status": item.status.value,
                    "history_count": item.summary.history_count,
                    "download_count": item.summary.download_count,
                    "bookmark_count": item.summary.bookmark_count,
                    "search_count": item.summary.search_count,
                    "login_page_count": item.summary.login_page_count,
                    "cookie_metadata_count": item.summary.cookie_count,
                    "history": [
                        visit.model_dump(mode="json") for visit in item.history[:50]
                    ],
                    "downloads": [
                        row.model_dump(mode="json") for row in item.downloads[:50]
                    ],
                    "bookmarks": [
                        row.model_dump(mode="json") for row in item.bookmarks[:50]
                    ],
                    "searches": [
                        row.model_dump(mode="json") for row in item.searches[:50]
                    ],
                    "login_pages": [
                        row.model_dump(mode="json") for row in item.login_pages[:50]
                    ],
                    "cookie_metadata": cookie_meta[:50],
                }
            )
        )
        if item.status.value in {"partial", "error"}:
            limitations.append(
                f"Browser profile '{item.profile_path}' status={item.status.value}"
            )

    logger.info("Aggregated browser report section profiles=%d", len(profiles))
    return BrowserReportSection(
        available=True,
        profiles=profiles,
        history_count=history,
        download_count=downloads,
        bookmark_count=bookmarks,
        search_count=searches,
        login_page_count=logins,
        cookie_metadata_count=cookies,
        message=f"Browser artifacts aggregated from {len(profiles)} profile(s)",
        provenance={
            "service": "BrowserService",
            "phase": 5,
            "privacy": "cookie metadata only; values excluded",
        },
        limitations=limitations,
    )


def aggregate_timeline_section(
    timeline: TimelineResult | None,
    *,
    max_events: int = 500,
) -> TimelineReportSection | None:
    """Build a timeline report section from Phase 6 output."""
    if timeline is None:
        return None
    events = [
        sanitize_value(event.model_dump(mode="json"))
        for event in timeline.events[:max_events]
    ]
    limitations = list(timeline.warnings)
    if timeline.summary.total_events > len(events):
        limitations.append(
            f"Timeline list truncated to {len(events)} of "
            f"{timeline.summary.total_events} events"
        )
    # Surface naive-UTC policy when present on events.
    policies = {
        event.metadata.get("timezone_policy")
        for event in timeline.events
        if event.metadata.get("timezone_policy")
    }
    if "assumed_utc_naive" in policies:
        limitations.append(
            "Some timeline timestamps used assumed UTC for naive source values"
        )
    logger.info(
        "Aggregated timeline report section events=%d",
        timeline.summary.total_events,
    )
    return TimelineReportSection(
        available=True,
        total_events=timeline.summary.total_events,
        events_by_type=dict(sorted(timeline.summary.events_by_type.items())),
        events_by_source=dict(sorted(timeline.summary.events_by_source.items())),
        earliest_event=timeline.summary.earliest_event,
        latest_event=timeline.summary.latest_event,
        events=events,
        message=timeline.message,
        provenance={"service": "TimelineService", "phase": 6, "source": timeline.source},
        limitations=limitations,
    )


def aggregate_custody_section(
    *,
    events: Sequence[CustodyEvent] | None = None,
    verification: CustodyVerificationResult | None = None,
) -> CustodyReportSection | None:
    """Build a custody report section from Phase 7 output."""
    if events is None and verification is None:
        return None
    event_list = list(events or [])
    payload = [sanitize_value(event.model_dump(mode="json")) for event in event_list]
    limitations: list[str] = []
    chain_valid = None if verification is None else verification.valid
    if chain_valid is False:
        limitations.append("Custody hash-chain verification FAILED")
        if verification and verification.broken_event_id:
            limitations.append(
                f"First broken custody event_id={verification.broken_event_id}"
            )
    if verification and verification.warnings:
        limitations.extend(verification.warnings)

    message = "Custody events included"
    if verification is not None:
        message = verification.message
    logger.info(
        "Aggregated custody report section events=%d valid=%s",
        len(event_list),
        chain_valid,
    )
    return CustodyReportSection(
        available=True,
        event_count=len(event_list),
        events=payload,
        chain_valid=chain_valid,
        verification_message=None if verification is None else verification.message,
        broken_event_id=None if verification is None else verification.broken_event_id,
        first_event_id=event_list[0].event_id if event_list else None,
        last_event_id=event_list[-1].event_id if event_list else None,
        message=message,
        provenance={
            "service": "CustodyService",
            "phase": 7,
            "note": "event_hash values are custody ledger hashes, not evidence SHA-256",
        },
        limitations=limitations,
    )
