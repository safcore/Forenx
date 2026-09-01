"""Build complete ``ForensicReport`` documents from aggregated sections."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from app.reports.aggregator import (
    aggregate_browser_section,
    aggregate_custody_section,
    aggregate_hash_section,
    aggregate_keyword_section,
    aggregate_metadata_section,
    aggregate_timeline_section,
)
from app.reports.models import REPORT_VERSION, make_report_id, utc_now
from app.schemas.browser import BrowserResult
from app.schemas.custody import CustodyEvent, CustodyVerificationResult
from app.schemas.hash import HashResult, HashVerificationResult, IntegrityResult
from app.schemas.keyword import KeywordResult, SearchResult
from app.schemas.metadata import MetadataResult
from app.schemas.ai import AIAnalysis
from app.schemas.report import (
    EvidenceSummary,
    Finding,
    FindingSeverity,
    ForensicReport,
    InvestigationNote,
    InvestigationNotes,
    ReportMetadata,
    ReportStatus,
)
from app.schemas.timeline import TimelineResult
from app.utils.exceptions import ReportError
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _require_id(value: str, field_name: str) -> str:
    if value is None or not str(value).strip():
        raise ReportError(f"{field_name} is required for report generation")
    return str(value).strip()


def _ensure_aware(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None:
        raise ReportError(f"{field_name} must be timezone-aware")
    return value


def build_executive_summary(
    *,
    case_id: str,
    evidence: EvidenceSummary,
    modules: list[str],
    integrity_status: str | None,
    custody_valid: bool | None,
    findings: list[Finding],
    limitations: list[str],
) -> dict[str, Any]:
    """Deterministic template-based executive summary (no AI)."""
    important = [finding.title for finding in findings[:5]]
    return {
        "case_id": case_id,
        "evidence_id": evidence.evidence_id,
        "evidence_type": evidence.evidence_type,
        "evidence_size": evidence.file_size,
        "evidence_sha256": evidence.evidence_sha256,
        "analysis_modules_executed": modules,
        "important_findings": important,
        "custody_status": (
            "VALID"
            if custody_valid is True
            else "INVALID"
            if custody_valid is False
            else "NOT_PROVIDED"
        ),
        "integrity_status": integrity_status or "NOT_PROVIDED",
        "limitations_count": len(limitations),
    }


def derive_findings(
    *,
    evidence_id: str,
    hash_section,
    custody_section,
    keyword_section,
    timeline_section,
    generated_at: datetime,
) -> list[Finding]:
    """Create neutral, deterministic findings from aggregated sections."""
    findings: list[Finding] = []
    index = 1

    if hash_section is not None and hash_section.integrity_status:
        severity = (
            FindingSeverity.INFO
            if hash_section.integrity_verified
            else FindingSeverity.HIGH
        )
        findings.append(
            Finding(
                finding_id=f"F-{index:03d}",
                title="Evidence integrity check result",
                severity=severity,
                description=(
                    f"Integrity status reported as {hash_section.integrity_status} "
                    "for the evidence digest binding."
                ),
                evidence_reference=evidence_id,
                source="HashService",
                confidence=0.95,
                timestamp=generated_at,
            )
        )
        index += 1

    if keyword_section is not None and keyword_section.total_matches:
        findings.append(
            Finding(
                finding_id=f"F-{index:03d}",
                title="Keyword matches observed",
                severity=FindingSeverity.MEDIUM,
                description=(
                    f"{keyword_section.total_matches} keyword match(es) were "
                    "recorded during keyword search."
                ),
                evidence_reference=evidence_id,
                source="KeywordSearchService",
                confidence=0.85,
                timestamp=generated_at,
            )
        )
        index += 1

    if timeline_section is not None and timeline_section.total_events:
        findings.append(
            Finding(
                finding_id=f"F-{index:03d}",
                title="Timeline events reconstructed",
                severity=FindingSeverity.INFO,
                description=(
                    f"{timeline_section.total_events} timeline event(s) were "
                    "reconstructed from supported sources."
                ),
                evidence_reference=evidence_id,
                source="TimelineService",
                confidence=0.8,
                timestamp=generated_at,
            )
        )
        index += 1

    if custody_section is not None and custody_section.chain_valid is False:
        findings.append(
            Finding(
                finding_id=f"F-{index:03d}",
                title="Custody chain verification failed",
                severity=FindingSeverity.CRITICAL,
                description=(
                    "The supplied chain-of-custody hash chain did not verify. "
                    f"Broken event: {custody_section.broken_event_id or 'unknown'}."
                ),
                evidence_reference=evidence_id,
                source="CustodyService",
                confidence=0.99,
                timestamp=generated_at,
            )
        )
    return findings


def determine_status(
    *,
    hash_section,
    metadata_section,
    keyword_section,
    browser_section,
    timeline_section,
    custody_section,
    limitations: list[str],
) -> ReportStatus:
    """Compute SUCCESS / PARTIAL / FAILED without hiding failures."""
    sections = [
        hash_section,
        metadata_section,
        keyword_section,
        browser_section,
        timeline_section,
        custody_section,
    ]
    if all(section is None for section in sections):
        return ReportStatus.FAILED

    if custody_section is not None and custody_section.chain_valid is False:
        return ReportStatus.PARTIAL

    if limitations:
        return ReportStatus.PARTIAL

    optional_unavailable = any(
        section is not None and section.available is False
        for section in sections
        if section is not None
    )
    if optional_unavailable:
        return ReportStatus.PARTIAL
    return ReportStatus.SUCCESS


def build_forensic_report(
    *,
    case_id: str,
    evidence_id: str,
    title: str | None = None,
    investigator: str | None = None,
    evidence_path: str | None = None,
    original_filename: str | None = None,
    evidence_type: str | None = None,
    file_size: int | None = None,
    mime_type: str | None = None,
    report_id: str | None = None,
    generated_at: datetime | None = None,
    hash_results: Sequence[HashResult] | None = None,
    hash_verification: HashVerificationResult | None = None,
    integrity: IntegrityResult | None = None,
    metadata: MetadataResult | None = None,
    keyword: SearchResult | KeywordResult | None = None,
    browser: BrowserResult | Sequence[BrowserResult] | None = None,
    timeline: TimelineResult | None = None,
    custody_events: Sequence[CustodyEvent] | None = None,
    custody_verification: CustodyVerificationResult | None = None,
    investigation_notes: Sequence[InvestigationNote] | None = None,
    extra_limitations: Sequence[str] | None = None,
    conclusion: str | None = None,
    ai_analysis: AIAnalysis | None = None,
) -> ForensicReport:
    """Aggregate supplied forensic results into a complete report document.

    Raises:
        ReportError: When required identity fields are missing/invalid.
    """
    case = _require_id(case_id, "case_id")
    evidence = _require_id(evidence_id, "evidence_id")
    rid = report_id or make_report_id()
    if not str(rid).strip():
        raise ReportError("report_id must not be empty")
    stamp = _ensure_aware(generated_at or utc_now(), "generated_at")

    hash_section = aggregate_hash_section(
        hash_results=hash_results,
        verification=hash_verification,
        integrity=integrity,
        evidence_path=evidence_path,
    )
    metadata_section = aggregate_metadata_section(metadata)
    keyword_section = aggregate_keyword_section(keyword)
    browser_section = aggregate_browser_section(browser)
    timeline_section = aggregate_timeline_section(timeline)
    custody_section = aggregate_custody_section(
        events=custody_events,
        verification=custody_verification,
    )

    modules: list[str] = []
    if hash_section is not None:
        modules.append("hashing")
    if metadata_section is not None:
        modules.append("metadata")
    if keyword_section is not None:
        modules.append("keyword_search")
    if browser_section is not None:
        modules.append("browser_analysis")
    if timeline_section is not None:
        modules.append("timeline")
    if custody_section is not None:
        modules.append("custody")
    if ai_analysis is not None:
        modules.append("ai_assisted_analysis")

    sha256 = None
    if hash_section is not None:
        sha256 = hash_section.primary_sha256
    if sha256 is None and custody_events:
        sha256 = next(
            (event.evidence_sha256 for event in custody_events if event.evidence_sha256),
            None,
        )

    evidence_summary = EvidenceSummary(
        evidence_id=evidence,
        case_id=case,
        evidence_path=evidence_path,
        original_filename=original_filename,
        evidence_type=evidence_type or (
            metadata_section.file_type if metadata_section else None
        ),
        file_size=file_size,
        mime_type=mime_type,
        evidence_sha256=sha256,
        modules_executed=modules,
    )

    limitations: list[str] = list(extra_limitations or [])
    for section in (
        hash_section,
        metadata_section,
        keyword_section,
        browser_section,
        timeline_section,
        custody_section,
    ):
        if section is not None:
            limitations.extend(section.limitations)
    if ai_analysis is not None:
        limitations.extend(ai_analysis.limitations)
        limitations.append(
            "AI-ASSISTED ANALYSIS - NOT A SUBSTITUTE FOR FORENSIC FINDINGS"
        )

    findings = derive_findings(
        evidence_id=evidence,
        hash_section=hash_section,
        custody_section=custody_section,
        keyword_section=keyword_section,
        timeline_section=timeline_section,
        generated_at=stamp,
    )

    status = determine_status(
        hash_section=hash_section,
        metadata_section=metadata_section,
        keyword_section=keyword_section,
        browser_section=browser_section,
        timeline_section=timeline_section,
        custody_section=custody_section,
        limitations=limitations,
    )
    if status is ReportStatus.FAILED:
        raise ReportError(
            "Report generation failed: no forensic section data was supplied"
        )

    summary = build_executive_summary(
        case_id=case,
        evidence=evidence_summary,
        modules=modules,
        integrity_status=(
            None if hash_section is None else hash_section.integrity_status
        ),
        custody_valid=(
            None if custody_section is None else custody_section.chain_valid
        ),
        findings=findings,
        limitations=limitations,
    )

    if conclusion is None:
        if custody_section is not None and custody_section.chain_valid is False:
            conclusion_text = (
                "Report generated with an INVALID custody chain. Findings and "
                "section results are included for investigative review; the custody "
                "verification failure must not be treated as successful chain integrity."
            )
        elif status is ReportStatus.PARTIAL:
            conclusion_text = (
                "Report generated with PARTIAL coverage due to unavailable artifacts "
                "or reported limitations. Review the limitations section before relying "
                "on omitted or incomplete modules."
            )
        else:
            conclusion_text = (
                "Report generated successfully from the supplied forensic service "
                "results. This document is a derived artifact and does not modify "
                "source evidence."
            )
    else:
        conclusion_text = conclusion

    metadata_block = ReportMetadata(
        report_id=rid,
        case_id=case,
        evidence_id=evidence,
        title=title or f"ForenX Forensic Report — {case} / {evidence}",
        investigator=investigator,
        generated_at=stamp,
        timezone="UTC",
        report_version=REPORT_VERSION,
        provenance={
            "artifact_type": "derived_report",
            "engine": "ForenX",
            "phases_consumed": modules,
        },
    )

    report = ForensicReport(
        report_id=rid,
        case_id=case,
        evidence_id=evidence,
        title=metadata_block.title,
        investigator=investigator,
        generated_at=stamp,
        timezone="UTC",
        report_version=REPORT_VERSION,
        generation_status=status,
        executive_summary=summary,
        evidence_summary=evidence_summary,
        hash_results=hash_section,
        metadata_results=metadata_section,
        keyword_results=keyword_section,
        browser_results=browser_section,
        timeline_results=timeline_section,
        custody_results=custody_section,
        ai_analysis=ai_analysis,
        investigation_notes=InvestigationNotes(
            notes=list(investigation_notes or [])
        ),
        findings=findings,
        limitations=sorted(set(limitations)),
        conclusion=conclusion_text,
        provenance={
            "derived_artifact": True,
            "source_evidence_id": evidence,
            "services": modules,
            "generated_at": stamp.isoformat(),
        },
        report_metadata=metadata_block,
    )
    logger.info(
        "Built forensic report id=%s status=%s modules=%s",
        rid,
        status.value,
        ",".join(modules),
    )
    return report


def validate_report(report: ForensicReport) -> None:
    """Validate a constructed report document.

    Raises:
        ReportError: On structural / identity issues.
    """
    if not report.report_id.strip():
        raise ReportError("Invalid report: missing report_id")
    if not report.case_id.strip():
        raise ReportError("Invalid report: missing case_id")
    if not report.evidence_id.strip():
        raise ReportError("Invalid report: missing evidence_id")
    if report.generated_at.tzinfo is None:
        raise ReportError("Invalid report: generated_at must be timezone-aware")
    if report.generation_status not in ReportStatus:
        raise ReportError("Invalid report: unknown generation_status")
    for finding in report.findings:
        if finding.severity not in FindingSeverity:
            raise ReportError(f"Invalid finding severity: {finding.severity}")
        if not (0.0 <= finding.confidence <= 1.0):
            raise ReportError("Finding confidence must be within [0, 1]")
    if report.custody_results is not None and report.custody_results.chain_valid is False:
        if report.generation_status is ReportStatus.SUCCESS:
            raise ReportError(
                "Invalid report: SUCCESS status is not allowed when custody "
                "verification failed"
            )
