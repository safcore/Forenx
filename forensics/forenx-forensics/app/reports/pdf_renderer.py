"""PDF renderer for forensic reports using ReportLab."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.reports.models import utc_now
from app.schemas.report import ForensicReport, ReportGenerationResult
from app.utils.exceptions import ReportError
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ForenXTitle",
            parent=base["Title"],
            fontSize=18,
            spaceAfter=12,
            alignment=TA_LEFT,
        ),
        "heading": ParagraphStyle(
            "ForenXHeading",
            parent=base["Heading2"],
            fontSize=13,
            spaceBefore=14,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "ForenXBody",
            parent=base["BodyText"],
            fontSize=9,
            leading=12,
        ),
        "small": ParagraphStyle(
            "ForenXSmall",
            parent=base["BodyText"],
            fontSize=8,
            leading=10,
        ),
    }


def _p(text: Any, style: ParagraphStyle) -> Paragraph:
    safe = (
        str(text if text is not None else "—")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return Paragraph(safe, style)


def _kv_table(rows: list[tuple[str, Any]], styles: dict[str, ParagraphStyle]) -> Table:
    data = [[_p(key, styles["small"]), _p(value, styles["small"])] for key, value in rows]
    table = Table(data, colWidths=[2.2 * inch, 4.8 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F2F2F2")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _section_table(
    headers: list[str],
    rows: list[list[Any]],
    styles: dict[str, ParagraphStyle],
    col_widths: list[float] | None = None,
) -> Table:
    data = [[_p(h, styles["small"]) for h in headers]]
    for row in rows:
        data.append([_p(cell, styles["small"]) for cell in row])
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return table


def build_pdf_story(report: ForensicReport) -> list:
    """Build Platypus flowables for a forensic report."""
    styles = _styles()
    story: list = []

    story.append(_p(report.title, styles["title"]))
    story.append(
        _kv_table(
            [
                ("Report ID", report.report_id),
                ("Case ID", report.case_id),
                ("Evidence ID", report.evidence_id),
                ("Investigator", report.investigator or "—"),
                ("Generated At (UTC)", report.generated_at.isoformat()),
                ("Report Version", report.report_version),
                ("Status", report.generation_status.value),
            ],
            styles,
        )
    )
    story.append(Spacer(1, 0.2 * inch))

    story.append(_p("1. Case & Evidence Information", styles["heading"]))
    es = report.evidence_summary
    story.append(
        _kv_table(
            [
                ("Case ID", es.case_id),
                ("Evidence ID", es.evidence_id),
                ("Filename", es.original_filename or "—"),
                ("Path", es.evidence_path or "—"),
                ("Type", es.evidence_type or "—"),
                ("Size (bytes)", es.file_size if es.file_size is not None else "—"),
                ("MIME", es.mime_type or "—"),
                ("Evidence SHA-256", es.evidence_sha256 or "—"),
                ("Modules", ", ".join(es.modules_executed) or "—"),
            ],
            styles,
        )
    )

    story.append(_p("2. Executive Summary", styles["heading"]))
    for key, value in sorted(report.executive_summary.items()):
        story.append(_p(f"<b>{key}</b>: {value}", styles["body"]))

    story.append(_p("3. Hash & Integrity Results", styles["heading"]))
    if report.hash_results is None:
        story.append(_p("Hash section not supplied.", styles["body"]))
    else:
        hr = report.hash_results
        story.append(
            _kv_table(
                [
                    ("Evidence path", hr.evidence_path or "—"),
                    ("Primary SHA-256", hr.primary_sha256 or "—"),
                    ("Verification verified", hr.verification_verified),
                    ("Integrity status", hr.integrity_status or "—"),
                    ("Integrity verified", hr.integrity_verified),
                    ("Message", hr.message),
                    (
                        "Note",
                        "Evidence digests only; custody event hashes are separate",
                    ),
                ],
                styles,
            )
        )
        algo_rows = [[k, v] for k, v in sorted(hr.algorithms.items())]
        if algo_rows:
            story.append(Spacer(1, 0.1 * inch))
            story.append(
                _section_table(
                    ["Algorithm", "Evidence digest"],
                    algo_rows,
                    styles,
                    [1.5 * inch, 5.5 * inch],
                )
            )

    story.append(_p("4. Metadata", styles["heading"]))
    if report.metadata_results is None:
        story.append(_p("Metadata section not supplied.", styles["body"]))
    else:
        mr = report.metadata_results
        story.append(_p(f"File type: {mr.file_type or '—'}", styles["body"]))
        story.append(_p(mr.message or "", styles["body"]))
        for label, block in (
            ("Filesystem", mr.filesystem),
            ("Image", mr.image),
            ("PDF", mr.pdf),
            ("Document", mr.document),
        ):
            if not block:
                continue
            story.append(_p(label, styles["body"]))
            rows = [(str(k), block.get(k)) for k in sorted(block.keys())]
            story.append(_kv_table(rows, styles))
            story.append(Spacer(1, 0.08 * inch))

    story.append(_p("5. Keyword Findings", styles["heading"]))
    if report.keyword_results is None:
        story.append(_p("Keyword section not supplied.", styles["body"]))
    else:
        kr = report.keyword_results
        story.append(
            _kv_table(
                [
                    ("Keywords", ", ".join(kr.searched_keywords) or "—"),
                    ("Files searched", kr.total_files_searched),
                    ("Total matches", kr.total_matches),
                    ("Files with matches", kr.files_with_matches),
                    ("Frequency", kr.keyword_frequency),
                ],
                styles,
            )
        )
        match_rows = [
            [
                match.get("file_name"),
                match.get("keyword"),
                match.get("line_number") or match.get("page_number") or "—",
                match.get("context"),
            ]
            for match in kr.matches[:40]
        ]
        if match_rows:
            story.append(Spacer(1, 0.1 * inch))
            story.append(
                _section_table(
                    ["File", "Keyword", "Location", "Context"],
                    match_rows,
                    styles,
                    [1.4 * inch, 1.2 * inch, 0.8 * inch, 3.6 * inch],
                )
            )

    story.append(PageBreak())
    story.append(_p("6. Browser Artifacts", styles["heading"]))
    if report.browser_results is None:
        story.append(_p("Browser section not supplied.", styles["body"]))
    else:
        br = report.browser_results
        story.append(
            _kv_table(
                [
                    ("History count", br.history_count),
                    ("Downloads", br.download_count),
                    ("Bookmarks", br.bookmark_count),
                    ("Searches", br.search_count),
                    ("Login pages", br.login_page_count),
                    ("Cookie metadata entries", br.cookie_metadata_count),
                    ("Privacy", "Cookie values excluded"),
                ],
                styles,
            )
        )
        for profile in br.profiles[:5]:
            story.append(
                _p(
                    f"Profile: {profile.get('browser')} / {profile.get('profile_name')}",
                    styles["body"],
                )
            )

    story.append(_p("7. Timeline", styles["heading"]))
    if report.timeline_results is None:
        story.append(_p("Timeline section not supplied.", styles["body"]))
    else:
        tr = report.timeline_results
        story.append(
            _kv_table(
                [
                    ("Total events", tr.total_events),
                    ("By type", tr.events_by_type),
                    ("By source", tr.events_by_source),
                    ("Earliest", tr.earliest_event),
                    ("Latest", tr.latest_event),
                    ("Timezone policy", tr.timezone_policy),
                ],
                styles,
            )
        )
        timeline_rows = [
            [
                event.get("timestamp"),
                event.get("event_type"),
                event.get("source"),
                event.get("description"),
            ]
            for event in tr.events
        ]
        chunk_size = 35
        for start in range(0, len(timeline_rows), chunk_size):
            chunk = timeline_rows[start : start + chunk_size]
            story.append(Spacer(1, 0.08 * inch))
            story.append(
                _section_table(
                    ["Timestamp", "Type", "Source", "Description"],
                    chunk,
                    styles,
                    [1.6 * inch, 1.2 * inch, 1.2 * inch, 3.0 * inch],
                )
            )

    story.append(_p("8. Chain of Custody", styles["heading"]))
    if report.custody_results is None:
        story.append(_p("Custody section not supplied.", styles["body"]))
    else:
        cr = report.custody_results
        story.append(
            _kv_table(
                [
                    ("Event count", cr.event_count),
                    ("Chain valid", cr.chain_valid),
                    ("Verification", cr.verification_message or "—"),
                    ("Broken event", cr.broken_event_id or "—"),
                    ("First event", cr.first_event_id or "—"),
                    ("Last event", cr.last_event_id or "—"),
                ],
                styles,
            )
        )
        custody_rows = [
            [
                event.get("timestamp"),
                event.get("action"),
                event.get("actor_id"),
                event.get("evidence_sha256"),
                ((event.get("event_hash") or "")[:16] + "..."),
            ]
            for event in cr.events
        ]
        if custody_rows:
            story.append(Spacer(1, 0.08 * inch))
            story.append(
                _section_table(
                    ["Timestamp", "Action", "Actor", "Evidence SHA-256", "Event hash"],
                    custody_rows,
                    styles,
                    [1.4 * inch, 1.3 * inch, 1.0 * inch, 2.0 * inch, 1.3 * inch],
                )
            )

    story.append(_p("9. Findings", styles["heading"]))
    if not report.findings:
        story.append(_p("No structured findings generated.", styles["body"]))
    else:
        finding_rows = [
            [f.finding_id, f.severity.value, f.title, f.source, f.description]
            for f in report.findings
        ]
        story.append(
            _section_table(
                ["ID", "Severity", "Title", "Source", "Description"],
                finding_rows,
                styles,
                [0.7 * inch, 0.8 * inch, 1.4 * inch, 1.2 * inch, 2.9 * inch],
            )
        )

    story.append(
        _p(
            "10. AI-ASSISTED ANALYSIS - NOT A SUBSTITUTE FOR FORENSIC FINDINGS",
            styles["heading"],
        )
    )
    ai = report.ai_analysis
    if ai is None:
        story.append(
            _p(
                "AI-assisted analysis was not included in this report.",
                styles["body"],
            )
        )
    else:
        story.append(
            _kv_table(
                [
                    ("Status", ai.status.value),
                    ("Provider", ai.provider.value),
                    ("Model", ai.model),
                    ("Confidence", ai.confidence.value),
                    ("Analysis ID", ai.analysis_id),
                    ("Disclaimer", ai.disclaimer),
                ],
                styles,
            )
        )
        story.append(_p(ai.summary or "—", styles["body"]))
        if ai.findings:
            story.append(Spacer(1, 0.06 * inch))
            ai_rows = [
                [
                    f.finding_id,
                    f.kind.value,
                    f.title,
                    f.description,
                ]
                for f in ai.findings[:20]
            ]
            story.append(
                _section_table(
                    ["ID", "Kind", "Title", "Description"],
                    ai_rows,
                    styles,
                    [0.8 * inch, 1.1 * inch, 1.6 * inch, 3.5 * inch],
                )
            )
        if ai.investigation_questions:
            story.append(_p("Investigation Questions (advisory)", styles["heading"]))
            for q in ai.investigation_questions[:15]:
                story.append(
                    _p(f"• [{q.question_id}] {q.question}", styles["body"])
                )
        if ai.recommendations:
            story.append(_p("Recommendations (investigative leads)", styles["heading"]))
            for r in ai.recommendations[:15]:
                story.append(
                    _p(f"• [{r.recommendation_id}] {r.text}", styles["body"])
                )

    story.append(_p("11. Investigator Notes", styles["heading"]))
    notes = report.investigation_notes.notes
    if not notes:
        story.append(_p("No investigator notes supplied.", styles["body"]))
    else:
        for note in notes:
            story.append(
                _p(
                    f"[{note.category.value}] {note.author} @ "
                    f"{note.timestamp.isoformat()}: {note.note}",
                    styles["body"],
                )
            )

    story.append(_p("12. Limitations", styles["heading"]))
    if not report.limitations:
        story.append(_p("No limitations recorded.", styles["body"]))
    else:
        for item in report.limitations:
            story.append(_p(f"• {item}", styles["body"]))

    story.append(_p("13. Conclusion", styles["heading"]))
    story.append(_p(report.conclusion or "—", styles["body"]))

    story.append(_p("14. Provenance / Methodology", styles["heading"]))
    story.append(
        _p(
            "This report is a derived artifact produced by ForenX ReportService. "
            "It aggregates outputs from existing forensic services. Source evidence "
            "files are not modified. AI-assisted sections, when present, are "
            "advisory only and do not constitute independent forensic evidence.",
            styles["body"],
        )
    )
    story.append(
        _kv_table([(k, v) for k, v in sorted(report.provenance.items())], styles)
    )
    return story


def write_report_pdf(report: ForensicReport, output_path: Path) -> ReportGenerationResult:
    """Render and write a PDF report."""
    if output_path.suffix.lower() != ".pdf":
        raise ReportError("PDF report output path must end with .pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title=report.title,
        author=report.investigator or "ForenX",
    )
    doc.build(build_pdf_story(report))
    if not output_path.is_file() or output_path.stat().st_size <= 0:
        raise ReportError(f"PDF report was not written correctly: {output_path}")
    logger.info("Wrote PDF report path=%s id=%s", output_path, report.report_id)
    return ReportGenerationResult(
        status=report.generation_status,
        report_id=report.report_id,
        case_id=report.case_id,
        evidence_id=report.evidence_id,
        output_format="pdf",
        output_path=str(output_path),
        message="PDF report written successfully",
        generated_at=utc_now(),
        warnings=list(report.limitations),
    )
