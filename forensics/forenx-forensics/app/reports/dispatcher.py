"""Dispatch report rendering to JSON / PDF writers under outputs/reports/."""

from __future__ import annotations

from pathlib import Path

from app.reports.builder import validate_report
from app.reports.json_renderer import write_report_json
from app.reports.models import resolve_report_output_path
from app.reports.pdf_renderer import write_report_pdf
from app.schemas.report import ForensicReport, ReportGenerationResult
from app.utils.exceptions import ReportError
from app.utils.logger import get_logger

logger = get_logger(__name__)


def dispatch_report_output(
    report: ForensicReport,
    *,
    output_format: str,
    output_dir: Path | None = None,
    output_path: Path | None = None,
) -> ReportGenerationResult:
    """Validate a report and write it in the requested format."""
    validate_report(report)
    fmt = str(output_format).strip().lower()
    if fmt not in {"json", "pdf"}:
        raise ReportError(f"Invalid output format: {output_format!r}")

    if output_path is not None:
        path = Path(output_path)
        # Reject path traversal / absolute escapes outside resolved parents later
        # via resolve + containment checks in resolve_report_output_path for default
        # paths. Explicit paths must not contain `..` segments.
        if ".." in path.parts:
            raise ReportError(f"Path traversal rejected for report output: {path}")
        target = path
    else:
        target = resolve_report_output_path(
            case_id=report.case_id,
            evidence_id=report.evidence_id,
            output_format=fmt,
            output_dir=output_dir,
        )

    logger.info(
        "Dispatching report output format=%s path=%s report_id=%s",
        fmt,
        target,
        report.report_id,
    )
    if fmt == "json":
        return write_report_json(report, target)
    return write_report_pdf(report, target)
