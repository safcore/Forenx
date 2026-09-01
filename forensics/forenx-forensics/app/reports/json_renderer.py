"""Deterministic JSON renderer for forensic reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.reports.models import sanitize_value, utc_now
from app.schemas.report import ForensicReport, ReportGenerationResult, ReportStatus
from app.utils.exceptions import ReportError
from app.utils.logger import get_logger

logger = get_logger(__name__)


def report_to_canonical_dict(report: ForensicReport) -> dict[str, Any]:
    """Convert a report to a sanitized JSON-serializable dictionary."""
    payload = sanitize_value(report.model_dump(mode="json"))
    # Stable top-level ordering for readability; dumps still sorts all keys.
    return {
        "report_id": payload["report_id"],
        "case_id": payload["case_id"],
        "evidence_id": payload["evidence_id"],
        "title": payload["title"],
        "investigator": payload.get("investigator"),
        "generated_at": payload["generated_at"],
        "timezone": payload["timezone"],
        "report_version": payload["report_version"],
        "status": payload["generation_status"],
        "executive_summary": payload.get("executive_summary") or {},
        "evidence_summary": payload.get("evidence_summary") or {},
        "sections": {
            "hash": payload.get("hash_results"),
            "metadata": payload.get("metadata_results"),
            "keyword": payload.get("keyword_results"),
            "browser": payload.get("browser_results"),
            "timeline": payload.get("timeline_results"),
            "custody": payload.get("custody_results"),
            "ai": payload.get("ai_analysis"),
        },
        "findings": payload.get("findings") or [],
        "investigation_notes": payload.get("investigation_notes") or {"notes": []},
        "limitations": payload.get("limitations") or [],
        "conclusion": payload.get("conclusion") or "",
        "provenance": payload.get("provenance") or {},
        "report_metadata": payload.get("report_metadata"),
    }


def dumps_report_json(report: ForensicReport) -> str:
    """Serialize a report to deterministic UTF-8 JSON text."""
    payload = report_to_canonical_dict(report)
    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        separators=(",", ": "),
    )


def write_report_json(report: ForensicReport, output_path: Path) -> ReportGenerationResult:
    """Write a JSON report to disk as a derived artifact."""
    if output_path.suffix.lower() != ".json":
        raise ReportError("JSON report output path must end with .json")
    text = dumps_report_json(report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    logger.info("Wrote JSON report path=%s id=%s", output_path, report.report_id)
    return ReportGenerationResult(
        status=report.generation_status,
        report_id=report.report_id,
        case_id=report.case_id,
        evidence_id=report.evidence_id,
        output_format="json",
        output_path=str(output_path),
        message="JSON report written successfully",
        generated_at=utc_now(),
        warnings=list(report.limitations),
    )
