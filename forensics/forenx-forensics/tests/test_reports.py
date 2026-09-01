"""Tests for Phase 8 forensic report generation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.custody.verifier import verify_custody_chain
from app.reports.models import sanitize_value
from app.schemas.custody import CustodyAction
from app.schemas.report import (
    FindingSeverity,
    ForensicReport,
    InvestigationNote,
    NoteCategory,
    ReportStatus,
)
from app.services.browser_service import BrowserService
from app.services.custody_service import CustodyService
from app.services.hash_service import HashService
from app.services.keyword_service import KeywordSearchService
from app.services.metadata_service import MetadataService
from app.services.report_service import ReportService
from app.services.timeline_service import TimelineService
from app.utils.exceptions import ReportError
from tests.browser_fixtures import build_chromium_profile


@pytest.fixture
def report_service(tmp_path: Path) -> ReportService:
    return ReportService(output_dir=tmp_path / "reports")


@pytest.fixture
def sample_text(tmp_path: Path) -> Path:
    path = tmp_path / "evidence.txt"
    path.write_text("confidential budget bitcoin transfer notes\n", encoding="utf-8")
    return path


def _build_full_inputs(sample_text: Path, tmp_path: Path):
    hash_service = HashService()
    hashes = hash_service.calculate_hashes(sample_text)
    sha256 = next(item.hash for item in hashes if item.algorithm == "sha256")
    verification = hash_service.verify(sample_text, sha256, "sha256")
    integrity = hash_service.integrity_check(sample_text, sha256, "sha256")

    metadata = None
    try:
        metadata = MetadataService(hash_service=hash_service).extract(sample_text)
    except Exception:
        metadata = None

    keyword = KeywordSearchService().search(sample_text, "confidential")

    chrome = build_chromium_profile(tmp_path / "Chrome" / "User Data" / "Default")
    browser = BrowserService().analyze_browser(chrome)

    timeline = TimelineService().build_from_file(sample_text, include_metadata=False)

    custody = CustodyService(hash_service=hash_service)
    custody.record_event(
        evidence_id="EV-RPT-1",
        action=CustodyAction.EVIDENCE_ACQUIRED,
        description="Acquired for reporting demo",
        actor_id="inv-1",
        actor_role="investigator",
        evidence_sha256=sha256,
        evidence_path=str(sample_text),
        timestamp=datetime(2024, 8, 1, 10, 0, tzinfo=timezone.utc),
    )
    custody.record_event(
        evidence_id="EV-RPT-1",
        action=CustodyAction.EVIDENCE_ANALYZED,
        description="Analyzed for report",
        actor_id="an-1",
        actor_role="analyst",
        evidence_sha256=sha256,
        timestamp=datetime(2024, 8, 1, 11, 0, tzinfo=timezone.utc),
    )
    verification_chain = custody.verify_chain("EV-RPT-1")
    return {
        "hashes": hashes,
        "verification": verification,
        "integrity": integrity,
        "metadata": metadata,
        "keyword": keyword,
        "browser": browser,
        "timeline": timeline,
        "custody_events": custody.get_chain("EV-RPT-1"),
        "custody_verification": verification_chain,
        "sha256": sha256,
    }


class TestReportBuilding:
    def test_report_schema_creation(
        self, report_service: ReportService, sample_text: Path, tmp_path: Path
    ) -> None:
        data = _build_full_inputs(sample_text, tmp_path)
        report = report_service.build_report(
            case_id="CASE-8",
            evidence_id="EV-RPT-1",
            investigator="Demo Investigator",
            evidence_path=str(sample_text),
            original_filename=sample_text.name,
            file_size=sample_text.stat().st_size,
            hash_results=data["hashes"],
            hash_verification=data["verification"],
            integrity=data["integrity"],
            metadata=data["metadata"],
            keyword=data["keyword"],
            browser=data["browser"],
            timeline=data["timeline"],
            custody_events=data["custody_events"],
            custody_verification=data["custody_verification"],
            investigation_notes=[
                InvestigationNote(
                    author="Demo Investigator",
                    timestamp=datetime(2024, 8, 1, 12, 0, tzinfo=timezone.utc),
                    note="Initial review completed",
                    category=NoteCategory.OBSERVATION,
                )
            ],
        )
        assert isinstance(report, ForensicReport)
        assert report.report_id
        assert report.case_id == "CASE-8"
        assert report.evidence_id == "EV-RPT-1"
        assert report.evidence_summary.evidence_sha256 == data["sha256"]
        assert report.hash_results is not None
        assert report.keyword_results is not None
        assert report.browser_results is not None
        assert report.timeline_results is not None
        assert report.custody_results is not None
        assert report.investigation_notes.notes
        assert report.provenance.get("derived_artifact") is True
        assert report.generation_status in {ReportStatus.SUCCESS, ReportStatus.PARTIAL}

    def test_evidence_summary_and_sections(
        self, report_service: ReportService, sample_text: Path, tmp_path: Path
    ) -> None:
        data = _build_full_inputs(sample_text, tmp_path)
        report = report_service.build_report(
            case_id="CASE-8",
            evidence_id="EV-RPT-1",
            evidence_path=str(sample_text),
            hash_results=data["hashes"],
            integrity=data["integrity"],
            keyword=data["keyword"],
            browser=data["browser"],
            timeline=data["timeline"],
            custody_events=data["custody_events"],
            custody_verification=data["custody_verification"],
        )
        assert report.evidence_summary.modules_executed
        assert "sha256" in report.hash_results.algorithms
        assert report.keyword_results.total_matches >= 1
        assert report.browser_results.history_count >= 1
        assert report.timeline_results.total_events >= 1
        assert report.custody_results.chain_valid is True


class TestCustodyInReports:
    def test_valid_custody_chain_reporting(
        self, report_service: ReportService, sample_text: Path, tmp_path: Path
    ) -> None:
        data = _build_full_inputs(sample_text, tmp_path)
        report = report_service.build_report(
            case_id="CASE-8",
            evidence_id="EV-RPT-1",
            hash_results=data["hashes"],
            custody_events=data["custody_events"],
            custody_verification=data["custody_verification"],
        )
        assert report.custody_results.chain_valid is True
        assert report.generation_status is not ReportStatus.FAILED

    def test_invalid_custody_chain_reporting(
        self, report_service: ReportService, sample_text: Path, tmp_path: Path
    ) -> None:
        data = _build_full_inputs(sample_text, tmp_path)
        mutated = [item.model_copy(deep=True) for item in data["custody_events"]]
        mutated[1] = mutated[1].model_copy(update={"description": "tampered"})
        bad = verify_custody_chain(mutated)
        assert bad.valid is False
        report = report_service.build_report(
            case_id="CASE-8",
            evidence_id="EV-RPT-1",
            hash_results=data["hashes"],
            custody_events=mutated,
            custody_verification=bad,
        )
        assert report.custody_results.chain_valid is False
        assert report.generation_status is ReportStatus.PARTIAL
        assert any("INVALID" in item.upper() or "failed" in item.lower() for item in report.limitations)
        assert any(f.severity is FindingSeverity.CRITICAL for f in report.findings)


class TestReportOutputs:
    def test_json_and_pdf_generation(
        self, report_service: ReportService, sample_text: Path, tmp_path: Path
    ) -> None:
        data = _build_full_inputs(sample_text, tmp_path)
        report = report_service.build_report(
            case_id="CASE-8",
            evidence_id="EV-RPT-1",
            evidence_path=str(sample_text),
            original_filename=sample_text.name,
            hash_results=data["hashes"],
            hash_verification=data["verification"],
            integrity=data["integrity"],
            keyword=data["keyword"],
            browser=data["browser"],
            timeline=data["timeline"],
            custody_events=data["custody_events"],
            custody_verification=data["custody_verification"],
            generated_at=datetime(2024, 8, 1, 15, 0, tzinfo=timezone.utc),
            report_id="11111111-1111-1111-1111-111111111111",
        )
        json_result = report_service.generate_json(report)
        pdf_result = report_service.generate_pdf(report)
        json_path = Path(json_result.output_path)
        pdf_path = Path(pdf_result.output_path)
        assert json_path.is_file() and json_path.stat().st_size > 0
        assert pdf_path.is_file() and pdf_path.stat().st_size > 0
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert payload["report_id"] == report.report_id
        assert payload["status"] in {"SUCCESS", "PARTIAL"}
        assert "cookie_value" not in json_path.read_text(encoding="utf-8").lower()

    def test_deterministic_json(
        self, report_service: ReportService, sample_text: Path, tmp_path: Path
    ) -> None:
        data = _build_full_inputs(sample_text, tmp_path)
        common = dict(
            case_id="CASE-8",
            evidence_id="EV-RPT-1",
            hash_results=data["hashes"],
            integrity=data["integrity"],
            keyword=data["keyword"],
            generated_at=datetime(2024, 8, 1, 15, 0, tzinfo=timezone.utc),
            report_id="22222222-2222-2222-2222-222222222222",
        )
        first = report_service.dumps_json(report_service.build_report(**common))
        second = report_service.dumps_json(report_service.build_report(**common))
        assert first == second

    def test_invalid_output_format(
        self, report_service: ReportService, sample_text: Path, tmp_path: Path
    ) -> None:
        data = _build_full_inputs(sample_text, tmp_path)
        report = report_service.build_report(
            case_id="CASE-8",
            evidence_id="EV-RPT-1",
            hash_results=data["hashes"],
        )
        with pytest.raises(ReportError, match="format"):
            report_service.generate_report(report, output_format="html")

    def test_path_traversal_protection(
        self, report_service: ReportService, sample_text: Path, tmp_path: Path
    ) -> None:
        data = _build_full_inputs(sample_text, tmp_path)
        report = report_service.build_report(
            case_id="CASE-8",
            evidence_id="EV-RPT-1",
            hash_results=data["hashes"],
        )
        with pytest.raises(ReportError):
            report_service.generate_json(
                report,
                output_path=tmp_path / ".." / "evil.json",
            )

    def test_secret_sanitization(self) -> None:
        cleaned = sanitize_value(
            {"host": "example.com", "cookie_value": "SECRET", "nested": {"password": "x"}}
        )
        assert cleaned["cookie_value"] == "[REDACTED]"
        assert cleaned["nested"]["password"] == "[REDACTED]"
        assert cleaned["host"] == "example.com"


class TestReportStatusAndValidation:
    def test_partial_status_for_limitations(
        self, report_service: ReportService, sample_text: Path
    ) -> None:
        hashes = HashService().calculate_hashes(sample_text)
        report = report_service.build_report(
            case_id="CASE-8",
            evidence_id="EV-RPT-1",
            hash_results=hashes,
            extra_limitations=["browser database inaccessible"],
        )
        assert report.generation_status is ReportStatus.PARTIAL
        assert "browser database inaccessible" in report.limitations

    def test_failed_when_no_sections(self, report_service: ReportService) -> None:
        with pytest.raises(ReportError, match="no forensic section"):
            report_service.build_report(case_id="CASE-8", evidence_id="EV-RPT-1")

    def test_missing_ids_rejected(self, report_service: ReportService, sample_text: Path) -> None:
        hashes = HashService().calculate_hashes(sample_text)
        with pytest.raises(ReportError, match="case_id"):
            report_service.build_report(
                case_id=" ",
                evidence_id="EV-1",
                hash_results=hashes,
            )

    def test_report_validation(
        self, report_service: ReportService, sample_text: Path, tmp_path: Path
    ) -> None:
        data = _build_full_inputs(sample_text, tmp_path)
        report = report_service.build_report(
            case_id="CASE-8",
            evidence_id="EV-RPT-1",
            hash_results=data["hashes"],
            custody_events=data["custody_events"],
            custody_verification=data["custody_verification"],
        )
        report_service.validate_report(report)

    def test_findings_and_notes(
        self, report_service: ReportService, sample_text: Path, tmp_path: Path
    ) -> None:
        data = _build_full_inputs(sample_text, tmp_path)
        report = report_service.build_report(
            case_id="CASE-8",
            evidence_id="EV-RPT-1",
            hash_results=data["hashes"],
            integrity=data["integrity"],
            keyword=data["keyword"],
            investigation_notes=[
                InvestigationNote(
                    author="Lead",
                    timestamp=datetime(2024, 8, 1, tzinfo=timezone.utc),
                    note="Observed keyword activity",
                    category=NoteCategory.FINDING,
                )
            ],
        )
        assert report.findings
        assert report.investigation_notes.notes[0].category is NoteCategory.FINDING


class TestReportSafety:
    def test_read_only_evidence(
        self, report_service: ReportService, sample_text: Path, tmp_path: Path
    ) -> None:
        before = sample_text.read_bytes()
        data = _build_full_inputs(sample_text, tmp_path)
        report = report_service.build_report(
            case_id="CASE-8",
            evidence_id="EV-RPT-1",
            hash_results=data["hashes"],
            keyword=data["keyword"],
            browser=data["browser"],
            timeline=data["timeline"],
            custody_events=data["custody_events"],
            custody_verification=data["custody_verification"],
        )
        report_service.generate_report(report, output_format="json")
        report_service.generate_report(report, output_format="pdf")
        assert sample_text.read_bytes() == before

    def test_long_timeline_pdf(
        self, report_service: ReportService, sample_text: Path, tmp_path: Path
    ) -> None:
        data = _build_full_inputs(sample_text, tmp_path)
        # Expand timeline section by building from a directory with browser profile.
        profile = build_chromium_profile(tmp_path / "Chrome2" / "User Data" / "Default")
        case_dir = tmp_path / "case"
        case_dir.mkdir()
        target = case_dir / "note.txt"
        target.write_text(sample_text.read_text(encoding="utf-8"), encoding="utf-8")
        # copy profile under case
        import shutil

        shutil.copytree(profile, case_dir / "chrome" / "Default")
        timeline = TimelineService().build_from_directory(case_dir)
        report = report_service.build_report(
            case_id="CASE-LONG",
            evidence_id="EV-LONG",
            hash_results=data["hashes"],
            timeline=timeline,
            browser=data["browser"],
        )
        result = report_service.generate_pdf(report)
        assert Path(result.output_path).stat().st_size > 1000

    def test_empty_optional_sections(
        self, report_service: ReportService, sample_text: Path
    ) -> None:
        hashes = HashService().calculate_hashes(sample_text)
        report = report_service.build_report(
            case_id="CASE-8",
            evidence_id="EV-RPT-1",
            hash_results=hashes,
        )
        assert report.metadata_results is None
        assert report.browser_results is None
        assert report.generation_status in {ReportStatus.SUCCESS, ReportStatus.PARTIAL}

    def test_utf8_json_content(
        self, report_service: ReportService, sample_text: Path
    ) -> None:
        hashes = HashService().calculate_hashes(sample_text)
        report = report_service.build_report(
            case_id="CASE-Ü",
            evidence_id="EV-证据",
            hash_results=hashes,
            investigation_notes=[
                InvestigationNote(
                    author="分析员",
                    timestamp=datetime(2024, 8, 1, tzinfo=timezone.utc),
                    note="Unicode note — 检验",
                    category=NoteCategory.OBSERVATION,
                )
            ],
        )
        text = report_service.dumps_json(report)
        assert "检验" in text
        assert "\\u" not in text or "检验" in text

    def test_no_django_import(self) -> None:
        source = Path("app/services/report_service.py").read_text(encoding="utf-8")
        assert "import django" not in source
        assert "from django" not in source
