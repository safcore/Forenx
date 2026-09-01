"""ForenX Forensics Engine – Phase 2–9 demonstration entry point.

Initializes logging, verifies required directories, and demonstrates:

- Phase 2 evidence hashing via ``HashService``
- Phase 3 metadata extraction via ``MetadataService``
- Phase 4 keyword search via ``KeywordSearchService``
- Phase 5 browser analysis via ``BrowserService``
- Phase 6 timeline reconstruction via ``TimelineService``
- Phase 7 chain of custody via ``CustodyService``
- Phase 8 forensic report generation via ``ReportService``
- Phase 9 AI-assisted investigation via ``AIService`` (local/deterministic)

Business logic lives in the service layer; this module only formats demo output.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.schemas.custody import CustodyAction
from app.schemas.hash import HashResult, HashVerificationResult, IntegrityResult
from app.services.ai_service import AIService
from app.services.browser_service import BrowserService
from app.services.custody_service import CustodyService
from app.services.hash_service import HashService
from app.services.keyword_service import KeywordSearchService
from app.services.metadata_service import MetadataService
from app.services.report_service import ReportService
from app.services.timeline_service import TimelineService
from app.utils.config import (
    EVIDENCE_DIRECTORY,
    FORENX_AI_ENABLED,
    PROJECT_NAME,
    PROJECT_VERSION,
    REPORTS_DIRECTORY,
    REQUIRED_DIRECTORIES,
)
from app.utils.logger import get_logger, setup_logging


def ensure_directories(directories: tuple[Path, ...]) -> None:
    """Create required project directories if they are missing.

    Args:
        directories: Paths that must exist for the engine to run.
    """
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def _sample_case_dir() -> Path:
    """Return the sample_case evidence directory."""
    return EVIDENCE_DIRECTORY / "sample_case"


def _require_sample(name: str) -> Path:
    """Resolve a required sample evidence file.

    Args:
        name: Filename under ``evidence/sample_case/``.

    Returns:
        Path to the sample file.

    Raises:
        FileNotFoundError: If the sample does not exist.
    """
    path = _sample_case_dir() / name
    if not path.is_file():
        raise FileNotFoundError(
            f"Sample evidence not found: {path}. "
            "Restore files under evidence/sample_case/."
        )
    return path


def _print_hash_demo(
    evidence_path: Path,
    hash_results: list[HashResult],
    verification: HashVerificationResult,
    integrity: IntegrityResult,
) -> None:
    """Print a concise Phase 2 hashing summary."""
    print("Phase 2 - Evidence Hashing & Integrity")
    print("-" * 48)
    print(f"Evidence : {evidence_path.name}")
    print(f"Size     : {evidence_path.stat().st_size} bytes")
    print("Hashes")
    for item in hash_results:
        print(f"  {item.algorithm.upper():<8} {item.hash}")
    print(
        f"Verification : verified={verification.verified} "
        f"algorithm={verification.algorithm}"
    )
    print(
        f"Integrity    : status={integrity.status.value} "
        f"algorithm={integrity.algorithm}"
    )
    print()


def _print_metadata_section(title: str, mapping: dict[str, Any]) -> None:
    """Print a labeled metadata key/value section."""
    print(title)
    for key, value in mapping.items():
        print(f"  {key:<16} {value}")
    print()


def _print_metadata_demo(service: MetadataService) -> None:
    """Demonstrate Phase 3 metadata extraction for sample evidence."""
    print("Phase 3 - Metadata Extraction")
    print("-" * 48)

    image_path = _require_sample("sample_image.png")
    image = service.extract_image(image_path)
    _print_metadata_section(
        f"Image ({image_path.name})",
        {
            "status": image.status.value,
            "mime_type": image.mime_type,
            "size": image.file_size,
            "dimensions": f"{image.width}x{image.height}",
            "color_mode": image.color_mode,
            "camera_make": image.camera_make,
            "date_taken": image.date_taken,
        },
    )

    pdf_path = _require_sample("sample_document.pdf")
    pdf = service.extract_pdf(pdf_path)
    _print_metadata_section(
        f"PDF ({pdf_path.name})",
        {
            "status": pdf.status.value,
            "title": pdf.title,
            "author": pdf.author,
            "creator": pdf.creator,
            "pages": pdf.page_count,
            "encrypted": pdf.encrypted,
        },
    )

    docx_path = _require_sample("sample_document.docx")
    docx = service.extract_document(docx_path)
    _print_metadata_section(
        f"DOCX ({docx_path.name})",
        {
            "status": docx.status.value,
            "title": docx.title,
            "author": docx.author,
            "subject": docx.subject,
            "created": docx.created_date,
            "modified": docx.modified_date,
        },
    )

    combined = service.extract(image_path)
    print(
        f"Dispatch extract() => file_type={combined.file_type} "
        f"status={combined.status.value} sha256="
        f"{combined.filesystem.sha256 if combined.filesystem else None}"
    )
    print()


def _print_keyword_demo(service: KeywordSearchService) -> None:
    """Demonstrate Phase 4 keyword search for sample evidence."""
    print("=" * 25)
    print("Phase 4 - Keyword Search")
    print("=" * 25)
    print()

    notes_path = _require_sample("sample_notes.txt")
    keyword = "confidential"
    result = service.search(notes_path, keyword)

    print("Searching:")
    print(notes_path.name)
    print()
    print("Keyword:")
    print(keyword)
    print()
    print("Matches Found:")
    print(result.match_count)
    print()

    for match in result.matches:
        location = (
            f"Line {match.line_number}"
            if match.line_number is not None
            else "Match"
        )
        print(f"{location}:")
        print(f'"{match.context}"')
        print()

    directory_result = service.search_directory(
        _sample_case_dir(),
        ["confidential", "bitcoin", "malware", "dropbox", "usb", "salary"],
    )
    summary = directory_result.summary
    print("Summary:")
    print(f"Files searched: {summary.total_files_searched}")
    print(f"Files matched: {summary.files_with_matches}")
    print(f"Total matches: {summary.total_matches}")
    print()


def _print_browser_demo(service: BrowserService) -> None:
    """Demonstrate Phase 5 browser analysis for sample evidence."""
    print("=" * 26)
    print("Phase 5 - Browser Analysis")
    print("=" * 26)
    print()

    chrome_profile = _sample_case_dir() / "browser" / "chrome" / "Default"
    if not chrome_profile.is_dir():
        raise FileNotFoundError(
            f"Sample Chrome profile not found: {chrome_profile}. "
            "Restore evidence/sample_case/browser/chrome/Default."
        )

    result = service.analyze_browser(chrome_profile)
    print("Detected Browser:")
    print(result.browser)
    print()
    print("History:")
    print(f"{result.summary.history_count} records")
    print()
    print("Downloads:")
    print(f"{result.summary.download_count} records")
    print()
    print("Bookmarks:")
    print(result.summary.bookmark_count)
    print()
    print("Cookies:")
    print(f"{result.summary.cookie_count} metadata entries")
    print()
    print("Search Queries:")
    print(result.summary.search_count)
    print()
    print("Login Pages:")
    print(result.summary.login_page_count)
    print()


def _print_timeline_demo(service: TimelineService) -> None:
    """Demonstrate Phase 6 timeline reconstruction for sample evidence."""
    print("=" * 36)
    print("Phase 6 - Timeline Reconstruction")
    print("=" * 36)
    print()

    sample_root = _sample_case_dir()
    result = service.build_timeline(sample_root)
    print("Timeline source:")
    print(sample_root)
    print()
    print("Status:")
    print(result.status.value)
    print()
    print("Number of events:")
    print(result.summary.total_events)
    print()
    print("Earliest event:")
    print(result.summary.earliest_event)
    print()
    print("Latest event:")
    print(result.summary.latest_event)
    print()
    print("Event type summary:")
    for event_type, count in result.summary.events_by_type.items():
        print(f"  {event_type}: {count}")
    print()
    if result.warnings:
        print(f"Warnings: {len(result.warnings)}")
        print()


def _print_custody_demo(
    service: CustodyService,
    *,
    evidence_path: Path,
    evidence_sha256: str,
) -> str:
    """Demonstrate Phase 7 chain-of-custody recording and verification.

    Returns:
        The evidence_id used for the demo custody chain.
    """
    print("=" * 30)
    print("Phase 7 - Chain of Custody")
    print("=" * 30)
    print()

    evidence_id = "SAMPLE-EVIDENCE-001"
    print("Evidence identity:")
    print(evidence_id)
    print(evidence_path.name)
    print(evidence_sha256)
    print()

    service.record_event(
        evidence_id=evidence_id,
        action=CustodyAction.EVIDENCE_ACQUIRED,
        description="Synthetic acquisition of sample evidence",
        actor_id="demo-investigator",
        actor_role="investigator",
        source="main.py",
        evidence_sha256=evidence_sha256,
        evidence_path=str(evidence_path),
        original_filename=evidence_path.name,
        file_size=evidence_path.stat().st_size,
    )
    service.record_event(
        evidence_id=evidence_id,
        action=CustodyAction.EVIDENCE_EXAMINED,
        description="Initial forensic examination",
        actor_id="demo-investigator",
        actor_role="investigator",
        evidence_sha256=evidence_sha256,
    )
    service.record_event(
        evidence_id=evidence_id,
        action=CustodyAction.EVIDENCE_ANALYZED,
        description="Hash / metadata / timeline analysis completed",
        actor_id="demo-analyst",
        actor_role="analyst",
        evidence_sha256=evidence_sha256,
    )

    chain = service.get_chain(evidence_id)
    verification = service.verify_chain(evidence_id)
    print("Event count:")
    print(len(chain))
    print()
    print("Verification status:")
    print(f"valid={verification.valid}")
    print(verification.message)
    print()
    return evidence_id


def _print_report_demo(
    *,
    report_service: ReportService,
    evidence_path: Path,
    evidence_id: str,
    hash_results: list[HashResult],
    verification: HashVerificationResult,
    integrity: IntegrityResult,
    metadata_service: MetadataService,
    keyword_service: KeywordSearchService,
    browser_service: BrowserService,
    timeline_service: TimelineService,
    custody_service: CustodyService,
) -> dict[str, Any]:
    """Demonstrate Phase 8 JSON/PDF report generation from existing results."""
    print("=" * 34)
    print("Phase 8 - Forensic Report Generation")
    print("=" * 34)
    print()

    sha256 = next(item.hash for item in hash_results if item.algorithm == "sha256")
    image_path = _sample_case_dir() / "sample_image.png"
    metadata = (
        metadata_service.extract(image_path) if image_path.is_file() else None
    )
    keyword = keyword_service.search_directory(
        _sample_case_dir(),
        ["confidential", "bitcoin", "malware"],
    )
    chrome_profile = _sample_case_dir() / "browser" / "chrome" / "Default"
    browser = browser_service.analyze_browser(chrome_profile)
    timeline = timeline_service.build_timeline(_sample_case_dir())
    custody_events = custody_service.get_chain(evidence_id)
    custody_verification = custody_service.verify_chain(evidence_id)

    report = report_service.build_report(
        case_id="SAMPLE-CASE-001",
        evidence_id=evidence_id,
        title="ForenX Sample Investigation Report",
        investigator="Demo Investigator",
        evidence_path=str(evidence_path),
        original_filename=evidence_path.name,
        file_size=evidence_path.stat().st_size,
        hash_results=hash_results,
        hash_verification=verification,
        integrity=integrity,
        metadata=metadata,
        keyword=keyword,
        browser=browser,
        timeline=timeline,
        custody_events=custody_events,
        custody_verification=custody_verification,
    )
    json_result = report_service.generate_json(report)
    pdf_result = report_service.generate_pdf(report)

    print("Report generated successfully")
    print(f"Report ID: {report.report_id}")
    print(f"Case ID: {report.case_id}")
    print(f"Evidence ID: {report.evidence_id}")
    print(f"SHA-256: {sha256}")
    print(
        "Timeline events: "
        f"{0 if report.timeline_results is None else report.timeline_results.total_events}"
    )
    print(
        "Keyword matches: "
        f"{0 if report.keyword_results is None else report.keyword_results.total_matches}"
    )
    browser_count = 0
    if report.browser_results is not None:
        browser_count = (
            report.browser_results.history_count
            + report.browser_results.download_count
            + report.browser_results.bookmark_count
            + report.browser_results.search_count
        )
    print(f"Browser artifacts count: {browser_count}")
    print(
        "Custody event count: "
        f"{0 if report.custody_results is None else report.custody_results.event_count}"
    )
    print(
        "Custody verification status: "
        f"{None if report.custody_results is None else report.custody_results.chain_valid}"
    )
    print(f"PDF output path: {pdf_result.output_path}")
    print(f"JSON output path: {json_result.output_path}")
    print(f"Reports directory: {REPORTS_DIRECTORY}")
    print()
    return {
        "report": report,
        "sha256": sha256,
        "keyword": keyword,
        "browser": browser,
        "timeline": timeline,
        "custody_events": custody_events,
        "custody_verification": custody_verification,
        "metadata": metadata,
    }


def _print_ai_demo(
    *,
    evidence_path: Path,
    evidence_id: str,
    hash_results: list[HashResult],
    integrity: IntegrityResult,
    report_bundle: dict[str, Any],
    report_service: ReportService,
) -> None:
    """Demonstrate Phase 9 assistive AI analysis (local deterministic)."""
    print("=" * 34)
    print("Phase 9 - AI-Assisted Investigation")
    print("=" * 34)
    print()

    ai_notes = _sample_case_dir() / "ai" / "suspicious_notes.txt"
    target = ai_notes if ai_notes.is_file() else evidence_path
    hash_service = HashService()
    target_hashes = hash_service.calculate_hashes(target)
    target_sha = next(item.hash for item in target_hashes if item.algorithm == "sha256")
    target_integrity = hash_service.integrity_check(target, target_sha, "sha256")
    keyword = KeywordSearchService().search_multiple(
        target,
        ["confidential", "bitcoin", "phishing", "meeting"],
    )
    timeline = TimelineService().build_from_file(target, include_metadata=False)

    # Explicitly enable local provider for the demo even when config default is off.
    disabled = AIService(enabled=False).analyze(
        case_id="SAMPLE-CASE-001",
        evidence_id=evidence_id,
        hash_results=target_hashes,
        integrity=target_integrity,
    )
    analysis = AIService(enabled=True, provider_name="local", allow_network=False).analyze(
        case_id="SAMPLE-CASE-001",
        evidence_id=evidence_id,
        evidence_path=str(target),
        original_filename=target.name,
        hash_results=target_hashes,
        integrity=target_integrity,
        keyword=keyword,
        browser=report_bundle.get("browser"),
        timeline=timeline,
        custody_events=report_bundle.get("custody_events"),
        custody_verification=report_bundle.get("custody_verification"),
        findings=report_bundle["report"].findings,
        limitations=report_bundle["report"].limitations,
    )

    print("AI Analysis")
    print(f"Config default enabled : {FORENX_AI_ENABLED}")
    print(f"Disabled-mode status   : {disabled.status.value}")
    print(f"Status                 : {analysis.status.value}")
    print(f"Provider               : {analysis.provider.value}")
    print(f"Model                  : {analysis.model}")
    print(f"Confidence             : {analysis.confidence.value}")
    print(f"Summary                : {analysis.summary}")
    print(f"Findings               : {len(analysis.findings)}")
    for finding in analysis.findings[:5]:
        print(f"  - [{finding.kind.value}] {finding.title}")
    print(f"Questions              : {len(analysis.investigation_questions)}")
    for question in analysis.investigation_questions[:3]:
        print(f"  - {question.question}")
    print(f"Disclaimer             : {analysis.disclaimer}")
    print()

    report_with_ai = report_service.build_report(
        case_id="SAMPLE-CASE-001",
        evidence_id=evidence_id,
        title="ForenX Sample Investigation Report (with AI section)",
        investigator="Demo Investigator",
        evidence_path=str(target),
        original_filename=target.name,
        file_size=target.stat().st_size,
        hash_results=target_hashes,
        integrity=target_integrity,
        metadata=report_bundle.get("metadata"),
        keyword=keyword,
        browser=report_bundle.get("browser"),
        timeline=timeline,
        custody_events=report_bundle.get("custody_events"),
        custody_verification=report_bundle.get("custody_verification"),
        ai_analysis=analysis,
    )
    json_result = report_service.generate_json(
        report_with_ai,
        output_path=REPORTS_DIRECTORY / f"{report_with_ai.report_id}-with-ai.json",
    )
    print(f"Optional AI report JSON: {json_result.output_path}")
    print()


def main() -> None:
    """Bootstrap the engine and demonstrate Phase 2–9 features."""
    setup_logging()
    logger = get_logger("main")

    ensure_directories(REQUIRED_DIRECTORIES)
    logger.info("Required directories verified")

    print(f"{PROJECT_NAME}")
    print(f"Version {PROJECT_VERSION}")
    print()

    text_evidence = _require_sample("sample_evidence.txt")
    hash_service = HashService()
    hash_results = hash_service.calculate_hashes(text_evidence)
    sha256_result = next(item for item in hash_results if item.algorithm == "sha256")
    verification = hash_service.verify(
        text_evidence,
        expected_hash=sha256_result.hash,
        algorithm="sha256",
    )
    integrity = hash_service.integrity_check(
        text_evidence,
        original_hash=sha256_result.hash,
        algorithm="sha256",
    )
    _print_hash_demo(text_evidence, hash_results, verification, integrity)

    metadata_service = MetadataService(hash_service=hash_service)
    _print_metadata_demo(metadata_service)

    keyword_service = KeywordSearchService()
    _print_keyword_demo(keyword_service)

    browser_service = BrowserService()
    _print_browser_demo(browser_service)

    timeline_service = TimelineService(
        browser_service=browser_service,
        metadata_service=metadata_service,
    )
    _print_timeline_demo(timeline_service)

    custody_service = CustodyService(hash_service=hash_service)
    evidence_id = _print_custody_demo(
        custody_service,
        evidence_path=text_evidence,
        evidence_sha256=sha256_result.hash,
    )

    report_service = ReportService()
    report_bundle = _print_report_demo(
        report_service=report_service,
        evidence_path=text_evidence,
        evidence_id=evidence_id,
        hash_results=hash_results,
        verification=verification,
        integrity=integrity,
        metadata_service=metadata_service,
        keyword_service=keyword_service,
        browser_service=browser_service,
        timeline_service=timeline_service,
        custody_service=custody_service,
    )

    _print_ai_demo(
        evidence_path=text_evidence,
        evidence_id=evidence_id,
        hash_results=hash_results,
        integrity=integrity,
        report_bundle=report_bundle,
        report_service=report_service,
    )

    print("-" * 48)
    print(
        "Phase 2 + Phase 3 + Phase 4 + Phase 5 + Phase 6 + Phase 7 + Phase 8 "
        "+ Phase 9 Demonstrated Successfully"
    )


if __name__ == "__main__":
    main()
