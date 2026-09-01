"""Build bounded, sanitized forensic context for AI / fallback analysis."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from app.ai.models import sanitize_and_bound, suspicious_keyword_hits, utc_now
from app.schemas.ai import AIContextSummary
from app.schemas.browser import BrowserResult
from app.schemas.custody import CustodyEvent, CustodyVerificationResult
from app.schemas.hash import HashResult, IntegrityResult
from app.schemas.keyword import KeywordResult, SearchResult
from app.schemas.metadata import MetadataResult
from app.schemas.report import Finding, ForensicReport, InvestigationNote
from app.schemas.timeline import TimelineResult
from app.utils.config import (
    AI_MAX_BROWSER_ITEMS,
    AI_MAX_CUSTODY_EVENTS,
    AI_MAX_KEYWORD_MATCHES,
    AI_MAX_TIMELINE_EVENTS,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _module_list(**flags: bool) -> list[str]:
    return [name for name, present in flags.items() if present]


def build_ai_context(
    *,
    case_id: str,
    evidence_id: str,
    evidence_path: str | None = None,
    original_filename: str | None = None,
    evidence_sha256: str | None = None,
    hash_results: Sequence[HashResult] | None = None,
    integrity: IntegrityResult | None = None,
    metadata: MetadataResult | None = None,
    keyword: SearchResult | KeywordResult | None = None,
    browser: BrowserResult | Sequence[BrowserResult] | None = None,
    timeline: TimelineResult | None = None,
    custody_events: Sequence[CustodyEvent] | None = None,
    custody_verification: CustodyVerificationResult | None = None,
    findings: Sequence[Finding] | None = None,
    investigation_notes: Sequence[InvestigationNote] | None = None,
    limitations: Sequence[str] | None = None,
    generated_at: datetime | None = None,
    report: ForensicReport | None = None,
) -> AIContextSummary:
    """Construct a deterministic, redacted investigation context.

    Prefers already-aggregated report sections when ``report`` is provided.
    Never dumps unbounded evidence payloads into prompts.
    """
    truncation: list[str] = []
    stamp = generated_at or utc_now()

    # Prefer report-derived summaries when available (no re-extraction).
    if report is not None:
        case_id = report.case_id
        evidence_id = report.evidence_id
        evidence_sha256 = evidence_sha256 or report.evidence_summary.evidence_sha256
        findings = findings or report.findings
        investigation_notes = investigation_notes or report.investigation_notes.notes
        limitations = list(limitations or []) + list(report.limitations)

    algorithms: dict[str, str] = {}
    if hash_results:
        for item in hash_results:
            algorithms[item.algorithm.lower()] = item.hash
            evidence_sha256 = evidence_sha256 or (
                item.hash if item.algorithm.lower() == "sha256" else evidence_sha256
            )
    integrity_status = None
    if integrity is not None:
        integrity_status = integrity.status.value
        evidence_sha256 = evidence_sha256 or integrity.hash
    elif report is not None and report.hash_results is not None:
        integrity_status = report.hash_results.integrity_status
        algorithms = dict(report.hash_results.algorithms)
        evidence_sha256 = evidence_sha256 or report.hash_results.primary_sha256

    keyword_summary: dict[str, Any] = {}
    if keyword is not None:
        if isinstance(keyword, SearchResult):
            freq = dict(sorted(keyword.summary.keyword_frequency.items()))
            matches = []
            for result in keyword.results:
                for match in result.matches:
                    matches.append(
                        {
                            "file_name": match.file_name,
                            "keyword": match.keyword,
                            "context": match.context,
                            "line_number": match.line_number,
                            "page_number": match.page_number,
                        }
                    )
            if len(matches) > AI_MAX_KEYWORD_MATCHES:
                truncation.append(
                    f"Keyword matches truncated to {AI_MAX_KEYWORD_MATCHES}"
                )
            keyword_summary = {
                "total_matches": keyword.summary.total_matches,
                "files_searched": keyword.summary.total_files_searched,
                "keyword_frequency": freq,
                "suspicious_keyword_hits": suspicious_keyword_hits(freq),
                "matches": matches[:AI_MAX_KEYWORD_MATCHES],
            }
        else:
            freq = {
                key: sum(1 for match in keyword.matches if match.keyword == key)
                for key in keyword.keywords
            }
            matches = [
                {
                    "file_name": match.file_name,
                    "keyword": match.keyword,
                    "context": match.context,
                    "line_number": match.line_number,
                }
                for match in keyword.matches[:AI_MAX_KEYWORD_MATCHES]
            ]
            if keyword.match_count > len(matches):
                truncation.append(
                    f"Keyword matches truncated to {AI_MAX_KEYWORD_MATCHES}"
                )
            keyword_summary = {
                "total_matches": keyword.match_count,
                "files_searched": 1,
                "keyword_frequency": freq,
                "suspicious_keyword_hits": suspicious_keyword_hits(freq),
                "matches": matches,
            }
    elif report is not None and report.keyword_results is not None:
        kr = report.keyword_results
        matches = kr.matches[:AI_MAX_KEYWORD_MATCHES]
        if len(kr.matches) > AI_MAX_KEYWORD_MATCHES:
            truncation.append(f"Keyword matches truncated to {AI_MAX_KEYWORD_MATCHES}")
        keyword_summary = {
            "total_matches": kr.total_matches,
            "files_searched": kr.total_files_searched,
            "keyword_frequency": dict(kr.keyword_frequency),
            "suspicious_keyword_hits": suspicious_keyword_hits(kr.keyword_frequency),
            "matches": matches,
        }

    browser_summary: dict[str, Any] = {}
    if browser is not None:
        items = [browser] if isinstance(browser, BrowserResult) else list(browser)
        history = []
        downloads = []
        searches = []
        bookmarks = []
        for item in items:
            history.extend(
                {
                    "browser": visit.browser,
                    "url": visit.url,
                    "title": visit.title,
                    "visit_time": visit.visit_time.isoformat()
                    if visit.visit_time
                    else None,
                }
                for visit in item.history[:AI_MAX_BROWSER_ITEMS]
            )
            downloads.extend(
                {
                    "browser": row.browser,
                    "source_url": row.source_url,
                    "local_path": row.local_path,
                    "downloaded_time": row.downloaded_time.isoformat()
                    if row.downloaded_time
                    else None,
                }
                for row in item.downloads[:AI_MAX_BROWSER_ITEMS]
            )
            searches.extend(
                {
                    "browser": row.browser,
                    "engine": row.engine,
                    "search_query": row.search_query,
                    "visit_time": row.visit_time.isoformat() if row.visit_time else None,
                }
                for row in item.searches[:AI_MAX_BROWSER_ITEMS]
            )
            bookmarks.extend(
                {
                    "browser": row.browser,
                    "title": row.title,
                    "url": row.url,
                }
                for row in item.bookmarks[:AI_MAX_BROWSER_ITEMS]
            )
        browser_summary = {
            "profile_count": len(items),
            "history_count": sum(i.summary.history_count for i in items),
            "download_count": sum(i.summary.download_count for i in items),
            "search_count": sum(i.summary.search_count for i in items),
            "bookmark_count": sum(i.summary.bookmark_count for i in items),
            "cookie_metadata_count": sum(i.summary.cookie_count for i in items),
            "history": history[:AI_MAX_BROWSER_ITEMS],
            "downloads": downloads[:AI_MAX_BROWSER_ITEMS],
            "searches": searches[:AI_MAX_BROWSER_ITEMS],
            "bookmarks": bookmarks[:AI_MAX_BROWSER_ITEMS],
            "privacy": "cookie values excluded",
        }
        truncation.append("Browser artifact lists bounded for AI context")
    elif report is not None and report.browser_results is not None:
        br = report.browser_results
        browser_summary = {
            "profile_count": len(br.profiles),
            "history_count": br.history_count,
            "download_count": br.download_count,
            "search_count": br.search_count,
            "bookmark_count": br.bookmark_count,
            "cookie_metadata_count": br.cookie_metadata_count,
            "privacy": "cookie values excluded",
        }

    timeline_summary: dict[str, Any] = {}
    if timeline is not None:
        events = [
            {
                "event_id": event.event_id,
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type.value,
                "source": event.source,
                "description": event.description,
                "path": event.path,
            }
            for event in timeline.events[:AI_MAX_TIMELINE_EVENTS]
        ]
        if timeline.summary.total_events > len(events):
            truncation.append(
                f"Timeline events truncated to {AI_MAX_TIMELINE_EVENTS}"
            )
        timeline_summary = {
            "total_events": timeline.summary.total_events,
            "events_by_type": dict(timeline.summary.events_by_type),
            "events_by_source": dict(timeline.summary.events_by_source),
            "earliest_event": (
                timeline.summary.earliest_event.isoformat()
                if timeline.summary.earliest_event
                else None
            ),
            "latest_event": (
                timeline.summary.latest_event.isoformat()
                if timeline.summary.latest_event
                else None
            ),
            "events": events,
        }
    elif report is not None and report.timeline_results is not None:
        tr = report.timeline_results
        events = tr.events[:AI_MAX_TIMELINE_EVENTS]
        if tr.total_events > len(events):
            truncation.append(
                f"Timeline events truncated to {AI_MAX_TIMELINE_EVENTS}"
            )
        timeline_summary = {
            "total_events": tr.total_events,
            "events_by_type": dict(tr.events_by_type),
            "events_by_source": dict(tr.events_by_source),
            "earliest_event": tr.earliest_event.isoformat()
            if tr.earliest_event
            else None,
            "latest_event": tr.latest_event.isoformat() if tr.latest_event else None,
            "events": events,
        }

    custody_summary: dict[str, Any] = {}
    custody_valid = None
    if custody_verification is not None:
        custody_valid = custody_verification.valid
    elif report is not None and report.custody_results is not None:
        custody_valid = report.custody_results.chain_valid
    events_list = list(custody_events or [])
    if not events_list and report is not None and report.custody_results is not None:
        events_payload = report.custody_results.events[:AI_MAX_CUSTODY_EVENTS]
        custody_summary = {
            "event_count": report.custody_results.event_count,
            "chain_valid": custody_valid,
            "verification_message": report.custody_results.verification_message,
            "broken_event_id": report.custody_results.broken_event_id,
            "events": events_payload,
        }
    elif events_list or custody_verification is not None:
        payload = [
            {
                "event_id": event.event_id,
                "action": event.action.value,
                "timestamp": event.timestamp.isoformat(),
                "actor_id": event.actor_id,
                "description": event.description,
                "evidence_sha256": event.evidence_sha256,
                "event_hash": event.event_hash,
                "previous_event_hash": event.previous_event_hash,
            }
            for event in events_list[:AI_MAX_CUSTODY_EVENTS]
        ]
        if len(events_list) > AI_MAX_CUSTODY_EVENTS:
            truncation.append(f"Custody events truncated to {AI_MAX_CUSTODY_EVENTS}")
        custody_summary = {
            "event_count": len(events_list),
            "chain_valid": custody_valid,
            "verification_message": (
                None if custody_verification is None else custody_verification.message
            ),
            "broken_event_id": (
                None if custody_verification is None else custody_verification.broken_event_id
            ),
            "events": payload,
        }

    metadata_summary: dict[str, Any] = {}
    if metadata is not None:
        metadata_summary = {
            "file_type": metadata.file_type,
            "status": metadata.status.value,
            "message": metadata.message,
        }
    elif report is not None and report.metadata_results is not None:
        metadata_summary = {
            "file_type": report.metadata_results.file_type,
            "message": report.metadata_results.message,
        }

    findings_summary = [
        {
            "finding_id": item.finding_id,
            "title": item.title,
            "severity": item.severity.value,
            "source": item.source,
            "description": item.description,
        }
        for item in list(findings or [])[:20]
    ]
    notes_summary = [
        {
            "author": note.author,
            "category": note.category.value,
            "note": note.note,
            "timestamp": note.timestamp.isoformat(),
        }
        for note in list(investigation_notes or [])[:20]
    ]

    modules = _module_list(
        hashing=bool(algorithms or integrity_status),
        metadata=bool(metadata_summary),
        keyword_search=bool(keyword_summary),
        browser_analysis=bool(browser_summary),
        timeline=bool(timeline_summary),
        custody=bool(custody_summary),
    )

    context = AIContextSummary(
        case_id=case_id,
        evidence_id=evidence_id,
        generated_at=stamp,
        evidence_sha256=evidence_sha256,
        integrity_status=integrity_status,
        custody_valid=custody_valid,
        modules_present=modules,
        evidence_summary=sanitize_and_bound(
            {
                "evidence_path": evidence_path
                or (report.evidence_summary.evidence_path if report else None),
                "original_filename": original_filename
                or (report.evidence_summary.original_filename if report else None),
                "evidence_sha256": evidence_sha256,
            }
        ),
        hash_summary=sanitize_and_bound(
            {
                "algorithms": algorithms,
                "integrity_status": integrity_status,
                "primary_sha256": evidence_sha256,
            }
        ),
        metadata_summary=sanitize_and_bound(metadata_summary),
        keyword_summary=sanitize_and_bound(keyword_summary),
        browser_summary=sanitize_and_bound(browser_summary),
        timeline_summary=sanitize_and_bound(timeline_summary),
        custody_summary=sanitize_and_bound(custody_summary),
        findings_summary=sanitize_and_bound(findings_summary),
        notes_summary=sanitize_and_bound(notes_summary),
        limitations=sanitize_and_bound(list(limitations or [])),
        truncation_notes=truncation,
        provenance={
            "builder": "AIContextBuilder",
            "bounded": True,
            "sanitized": True,
            "cookie_values_excluded": True,
        },
    )
    logger.info(
        "Built AI context case_id=%s evidence_id=%s modules=%s",
        case_id,
        evidence_id,
        ",".join(modules),
    )
    return context
