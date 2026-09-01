"""Report generation service orchestration for the ForenX forensics engine.

Provides the public Phase 8 API for building and exporting forensic reports
from already-computed Phase 2–7 service results.

Typical usage example:

    from app.services.report_service import ReportService

    service = ReportService()
    report = service.build_report(case_id="CASE-1", evidence_id="EV-1", ...)
    service.generate_report(report, output_format="pdf")
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from app.reports.builder import build_forensic_report, validate_report
from app.reports.dispatcher import dispatch_report_output
from app.reports.json_renderer import dumps_report_json
from app.reports.models import REPORTS_OUTPUT_DIR
from app.schemas.browser import BrowserResult
from app.schemas.custody import CustodyEvent, CustodyVerificationResult
from app.schemas.hash import HashResult, HashVerificationResult, IntegrityResult
from app.schemas.keyword import KeywordResult, SearchResult
from app.schemas.metadata import MetadataResult
from app.schemas.ai import AIAnalysis
from app.schemas.report import (
    ForensicReport,
    InvestigationNote,
    ReportGenerationResult,
)
from app.schemas.timeline import TimelineResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ReportService:
    """High-level API for forensic report aggregation and export.

    Designed for reuse by CLI tools, tests, and a future Django backend.
    Does not modify evidence and does not reimplement Phase 2–7 analysis.
    """

    def __init__(self, *, output_dir: Path | None = None) -> None:
        """Initialize the report service.

        Args:
            output_dir: Optional override for report output directory
                (defaults to ``outputs/reports``).
        """
        self._output_dir = Path(output_dir) if output_dir else REPORTS_OUTPUT_DIR

    def build_report(
        self,
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
        """Build a ``ForensicReport`` from supplied forensic service results."""
        logger.info(
            "ReportService.build_report started case_id=%s evidence_id=%s",
            case_id,
            evidence_id,
        )
        report = build_forensic_report(
            case_id=case_id,
            evidence_id=evidence_id,
            title=title,
            investigator=investigator,
            evidence_path=evidence_path,
            original_filename=original_filename,
            evidence_type=evidence_type,
            file_size=file_size,
            mime_type=mime_type,
            report_id=report_id,
            generated_at=generated_at,
            hash_results=hash_results,
            hash_verification=hash_verification,
            integrity=integrity,
            metadata=metadata,
            keyword=keyword,
            browser=browser,
            timeline=timeline,
            custody_events=custody_events,
            custody_verification=custody_verification,
            investigation_notes=investigation_notes,
            extra_limitations=extra_limitations,
            conclusion=conclusion,
            ai_analysis=ai_analysis,
        )
        logger.info(
            "ReportService.build_report finished report_id=%s status=%s",
            report.report_id,
            report.generation_status.value,
        )
        return report

    def validate_report(self, report: ForensicReport) -> None:
        """Validate report identity/status/findings constraints."""
        validate_report(report)

    def generate_json(
        self,
        report: ForensicReport,
        *,
        output_path: str | Path | None = None,
    ) -> ReportGenerationResult:
        """Write a deterministic JSON report."""
        return dispatch_report_output(
            report,
            output_format="json",
            output_dir=self._output_dir,
            output_path=Path(output_path) if output_path else None,
        )

    def generate_pdf(
        self,
        report: ForensicReport,
        *,
        output_path: str | Path | None = None,
    ) -> ReportGenerationResult:
        """Write a PDF report."""
        return dispatch_report_output(
            report,
            output_format="pdf",
            output_dir=self._output_dir,
            output_path=Path(output_path) if output_path else None,
        )

    def generate_report(
        self,
        report: ForensicReport,
        *,
        output_format: str = "pdf",
        output_path: str | Path | None = None,
    ) -> ReportGenerationResult:
        """Write a report in ``json`` or ``pdf`` format."""
        logger.info(
            "ReportService.generate_report format=%s report_id=%s",
            output_format,
            report.report_id,
        )
        return dispatch_report_output(
            report,
            output_format=output_format,
            output_dir=self._output_dir,
            output_path=Path(output_path) if output_path else None,
        )

    def dumps_json(self, report: ForensicReport) -> str:
        """Return deterministic JSON text without writing to disk."""
        self.validate_report(report)
        return dumps_report_json(report)
