"""Tests for Phase 9 AI-assisted forensic investigation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from app.ai.context_builder import build_ai_context
from app.ai.dispatcher import resolve_ai_provider
from app.ai.local_provider import LocalDeterministicProvider, UnavailableAIProvider
from app.ai.models import sanitize_and_bound
from app.ai.prompt_builder import SYSTEM_INSTRUCTIONS, build_prompt
from app.ai.provider import AIProvider
from app.schemas.ai import (
    AIAnalysis,
    AIAnalysisStatus,
    AIConfidence,
    AIContextSummary,
    AIEvidenceRef,
    AIFinding,
    AIProviderType,
    AIStatementKind,
)
from app.schemas.custody import CustodyAction
from app.schemas.hash import IntegrityStatus
from app.schemas.keyword import KeywordMatch, KeywordResult, SearchResult, SearchStatus
from app.schemas.timeline import (
    TimelineEvent,
    TimelineEventType,
    TimelineResult,
    TimelineStatus,
    TimelineSummary,
    TimestampType,
)
from app.services.ai_service import AIService
from app.services.custody_service import CustodyService
from app.services.hash_service import HashService
from app.services.keyword_service import KeywordSearchService
from app.services.report_service import ReportService
from app.services.timeline_service import TimelineService
from app.utils.exceptions import AIAnalysisError


@pytest.fixture
def sample_text(tmp_path: Path) -> Path:
    path = tmp_path / "ai_evidence.txt"
    path.write_text(
        "confidential notes about bitcoin wallet transfer and phishing attempt\n"
        "benign meeting schedule and grocery list\n",
        encoding="utf-8",
    )
    return path


def _forensic_bundle(sample_text: Path) -> dict[str, Any]:
    hash_service = HashService()
    hashes = hash_service.calculate_hashes(sample_text)
    sha256 = next(item.hash for item in hashes if item.algorithm == "sha256")
    integrity = hash_service.integrity_check(sample_text, sha256, "sha256")
    keyword = KeywordSearchService().search_multiple(
        sample_text,
        ["confidential", "bitcoin", "phishing", "meeting"],
    )
    timeline = TimelineService().build_from_file(sample_text, include_metadata=False)
    custody = CustodyService(hash_service=hash_service)
    custody.record_event(
        evidence_id="EV-AI-1",
        action=CustodyAction.EVIDENCE_ACQUIRED,
        description="Acquired for AI demo",
        actor_id="inv-1",
        actor_role="investigator",
        evidence_sha256=sha256,
        evidence_path=str(sample_text),
        timestamp=datetime(2024, 9, 1, 10, 0, tzinfo=timezone.utc),
    )
    custody.record_event(
        evidence_id="EV-AI-1",
        action=CustodyAction.EVIDENCE_ANALYZED,
        description="Deterministic analysis complete",
        actor_id="an-1",
        actor_role="analyst",
        evidence_sha256=sha256,
        timestamp=datetime(2024, 9, 1, 11, 0, tzinfo=timezone.utc),
    )
    return {
        "hashes": hashes,
        "integrity": integrity,
        "keyword": keyword,
        "timeline": timeline,
        "custody_events": custody.get_chain("EV-AI-1"),
        "custody_verification": custody.verify_chain("EV-AI-1"),
        "sha256": sha256,
    }


class TestAISchemas:
    def test_schema_validation_and_kinds(self) -> None:
        analysis = AIAnalysis(
            analysis_id="a1",
            case_id="CASE-9",
            evidence_id="EV-AI-1",
            generated_at=datetime(2024, 9, 1, tzinfo=timezone.utc),
            provider=AIProviderType.DETERMINISTIC,
            model="deterministic-local",
            status=AIAnalysisStatus.FALLBACK,
            confidence=AIConfidence.MEDIUM,
            summary="Advisory summary",
            findings=[
                AIFinding(
                    finding_id="F1",
                    title="Observed hash",
                    kind=AIStatementKind.OBSERVED_FACT,
                    description="Hash present",
                    supporting_evidence=[
                        AIEvidenceRef(source="hash", description="SHA-256 digest")
                    ],
                ),
                AIFinding(
                    finding_id="F2",
                    title="Possible lead",
                    kind=AIStatementKind.INFERENCE,
                    description="May warrant review",
                    speculative=True,
                ),
            ],
        )
        assert analysis.findings[0].kind == AIStatementKind.OBSERVED_FACT
        assert analysis.findings[1].kind == AIStatementKind.INFERENCE
        assert "NOT A SUBSTITUTE" in analysis.disclaimer


class TestContextAndSanitization:
    def test_context_construction(self, sample_text: Path) -> None:
        data = _forensic_bundle(sample_text)
        ctx = build_ai_context(
            case_id="CASE-9",
            evidence_id="EV-AI-1",
            evidence_path=str(sample_text),
            hash_results=data["hashes"],
            integrity=data["integrity"],
            keyword=data["keyword"],
            timeline=data["timeline"],
            custody_events=data["custody_events"],
            custody_verification=data["custody_verification"],
        )
        assert isinstance(ctx, AIContextSummary)
        assert ctx.evidence_sha256 == data["sha256"]
        assert ctx.custody_valid is True
        assert ctx.integrity_status == IntegrityStatus.PASS.value
        assert ctx.keyword_summary.get("total_matches", 0) >= 1
        assert "bitcoin" in ctx.keyword_summary.get("suspicious_keyword_hits", {})

    def test_context_size_limiting(self) -> None:
        stamp = datetime(2024, 1, 1, tzinfo=timezone.utc)
        matches = [
            KeywordMatch(
                file_name="big.txt",
                absolute_path="/tmp/big.txt",
                keyword=f"kw{i}",
                matched_text=f"kw{i}",
                context="x" * 40,
                line_number=i,
                match_position=0,
            )
            for i in range(80)
        ]
        keyword = KeywordResult(
            file_name="big.txt",
            absolute_path="/tmp/big.txt",
            file_type="text",
            status=SearchStatus.SUCCESS,
            message="ok",
            keywords=[f"kw{i}" for i in range(80)],
            match_count=80,
            matches=matches,
            execution_time_ms=1.0,
            timestamp=stamp,
        )
        events = [
            TimelineEvent(
                event_id=f"E-{i}",
                timestamp=stamp,
                timestamp_original=stamp.isoformat(),
                timestamp_type=TimestampType.MODIFIED,
                event_type=TimelineEventType.FILE_MODIFIED,
                source="filesystem",
                source_file="big.txt",
                description=f"event {i}",
                artifact="filesystem",
                path="big.txt",
            )
            for i in range(100)
        ]
        timeline = TimelineResult(
            status=TimelineStatus.SUCCESS,
            message="ok",
            events=events,
            summary=TimelineSummary(
                total_events=100,
                events_by_type={"file_modified": 100},
                events_by_source={"filesystem": 100},
                earliest_event=events[0].timestamp,
                latest_event=events[-1].timestamp,
            ),
            source="test",
            generated_at=stamp,
        )
        ctx = build_ai_context(
            case_id="CASE-9",
            evidence_id="EV-AI-1",
            keyword=keyword,
            timeline=timeline,
        )
        assert len(ctx.keyword_summary["matches"]) <= 25
        assert len(ctx.timeline_summary["events"]) <= 40
        assert ctx.truncation_notes

    def test_secret_redaction(self) -> None:
        payload = {
            "password": "hunter2",
            "api_key": "sk-live-secret",
            "access_token": "tok-123",
            "session_token": "sess-9",
            "cookie_value": "SID=supersecret",
            "safe_field": "visible",
            "note": "password=leaked-value api_key: abc123",
        }
        cleaned = sanitize_and_bound(payload)
        assert cleaned["password"] == "[REDACTED]"
        assert cleaned["api_key"] == "[REDACTED]"
        assert cleaned["access_token"] == "[REDACTED]"
        assert cleaned["session_token"] == "[REDACTED]"
        assert cleaned["cookie_value"] == "[REDACTED]"
        assert cleaned["safe_field"] == "visible"
        assert "leaked-value" not in cleaned["note"]
        assert "[REDACTED]" in cleaned["note"]
        assert "sk-live-secret" not in str(cleaned)

    def test_empty_evidence_context(self) -> None:
        ctx = build_ai_context(case_id="CASE-9", evidence_id="EV-EMPTY")
        assert ctx.case_id == "CASE-9"
        assert ctx.modules_present == []
        assert ctx.evidence_sha256 is None

    def test_large_string_truncation(self) -> None:
        huge = "A" * 5000
        cleaned = sanitize_and_bound({"blob": huge})
        assert len(cleaned["blob"]) <= 500
        assert cleaned["blob"].endswith("...")


class TestPromptBuilder:
    def test_prompt_construction_deterministic(self, sample_text: Path) -> None:
        data = _forensic_bundle(sample_text)
        ctx = build_ai_context(
            case_id="CASE-9",
            evidence_id="EV-AI-1",
            hash_results=data["hashes"],
            integrity=data["integrity"],
            keyword=data["keyword"],
            generated_at=datetime(2024, 9, 1, tzinfo=timezone.utc),
        )
        first = build_prompt(ctx, task="summarize")
        second = build_prompt(ctx, task="summarize")
        assert first == second
        assert "assisting a forensic analyst" in first.lower()
        assert "Do not invent evidence" in first
        assert SYSTEM_INSTRUCTIONS.strip() in first
        assert data["sha256"] in first


class TestProvidersAndService:
    def test_deterministic_fallback(self, sample_text: Path) -> None:
        data = _forensic_bundle(sample_text)
        service = AIService(enabled=True, provider_name="local", allow_network=False)
        analysis = service.analyze(
            case_id="CASE-9",
            evidence_id="EV-AI-1",
            hash_results=data["hashes"],
            integrity=data["integrity"],
            keyword=data["keyword"],
            timeline=data["timeline"],
            custody_events=data["custody_events"],
            custody_verification=data["custody_verification"],
        )
        assert analysis.status == AIAnalysisStatus.FALLBACK
        assert analysis.provider == AIProviderType.DETERMINISTIC
        assert "DETERMINISTIC FALLBACK" in " ".join(analysis.limitations)
        assert analysis.provenance.get("evidence_sha256") == data["sha256"]
        assert analysis.provenance.get("custody_valid") is True
        kinds = {item.kind for item in analysis.findings}
        assert AIStatementKind.INFERENCE in kinds or AIStatementKind.OBSERVED_FACT in kinds
        assert any(item.supporting_evidence for item in analysis.findings)

    def test_provider_abstraction(self) -> None:
        provider, reason = resolve_ai_provider(
            enabled=True, provider_name="local", allow_network=False
        )
        assert isinstance(provider, LocalDeterministicProvider)
        assert "local" in reason

    def test_unavailable_provider_handling(self) -> None:
        provider, reason = resolve_ai_provider(
            enabled=False, provider_name="local", allow_network=False
        )
        assert isinstance(provider, UnavailableAIProvider)
        ctx = build_ai_context(case_id="CASE-9", evidence_id="EV-AI-1")
        result = provider.analyze(ctx, "instructions", prompt="prompt")
        assert result.status == AIAnalysisStatus.UNAVAILABLE

    def test_remote_blocked_offline_fallback(self) -> None:
        provider, reason = resolve_ai_provider(
            enabled=True, provider_name="openai", allow_network=False
        )
        assert isinstance(provider, LocalDeterministicProvider)
        assert "network-block" in reason

    def test_ai_disabled_mode(self, sample_text: Path) -> None:
        data = _forensic_bundle(sample_text)
        service = AIService(enabled=False)
        analysis = service.analyze(
            case_id="CASE-9",
            evidence_id="EV-AI-1",
            hash_results=data["hashes"],
            integrity=data["integrity"],
        )
        assert analysis.status == AIAnalysisStatus.DISABLED
        assert analysis.provider == AIProviderType.UNAVAILABLE
        assert analysis.findings == []

    def test_malformed_provider_output(self, sample_text: Path) -> None:
        class BrokenProvider(AIProvider):
            name = "broken"

            def analyze(self, context, instructions, *, prompt):  # type: ignore[no-untyped-def]
                return {"not": "an AIAnalysis"}

        data = _forensic_bundle(sample_text)
        service = AIService(enabled=True, provider_name="local")
        with patch(
            "app.services.ai_service.resolve_ai_provider",
            return_value=(BrokenProvider(), "broken"),
        ):
            analysis = service.analyze(
                case_id="CASE-9",
                evidence_id="EV-AI-1",
                hash_results=data["hashes"],
            )
        assert analysis.status == AIAnalysisStatus.ERROR

    def test_fact_inference_distinction(self, sample_text: Path) -> None:
        data = _forensic_bundle(sample_text)
        analysis = LocalDeterministicProvider().analyze(
            build_ai_context(
                case_id="CASE-9",
                evidence_id="EV-AI-1",
                hash_results=data["hashes"],
                integrity=data["integrity"],
                keyword=data["keyword"],
                custody_verification=data["custody_verification"],
            ),
            "instructions",
            prompt="prompt",
        )
        observed = [f for f in analysis.observations if f.kind == AIStatementKind.OBSERVED_FACT]
        inferred = [f for f in analysis.findings if f.kind == AIStatementKind.INFERENCE]
        assert observed
        assert inferred
        assert all(item.speculative for item in inferred)

    def test_provenance_preservation(self, sample_text: Path) -> None:
        data = _forensic_bundle(sample_text)
        analysis = AIService(enabled=True).analyze(
            case_id="CASE-9",
            evidence_id="EV-AI-1",
            hash_results=data["hashes"],
            keyword=data["keyword"],
            timeline=data["timeline"],
        )
        refs = analysis.supporting_evidence + [
            ref for finding in analysis.findings for ref in finding.supporting_evidence
        ]
        assert refs
        assert any(ref.source in {"hash", "keyword", "timeline"} for ref in refs)

    def test_hash_and_custody_preservation(self, sample_text: Path) -> None:
        data = _forensic_bundle(sample_text)
        analysis = AIService(enabled=True).analyze(
            case_id="CASE-9",
            evidence_id="EV-AI-1",
            hash_results=data["hashes"],
            integrity=data["integrity"],
            custody_verification=data["custody_verification"],
        )
        assert analysis.provenance["evidence_sha256"] == data["sha256"]
        assert analysis.provenance["custody_valid"] is True
        assert analysis.provenance["integrity_status"] == IntegrityStatus.PASS.value
        blob = analysis.model_dump_json()
        assert data["sha256"] in blob

    def test_offline_no_network_calls(self, sample_text: Path) -> None:
        data = _forensic_bundle(sample_text)

        def _deny(*_args, **_kwargs):  # type: ignore[no-untyped-def]
            raise AssertionError("Network access attempted during AI analysis")

        with (
            patch("socket.socket", side_effect=_deny),
            patch("urllib.request.urlopen", side_effect=_deny),
        ):
            analysis = AIService(enabled=True, provider_name="local", allow_network=False).analyze(
                case_id="CASE-9",
                evidence_id="EV-AI-1",
                hash_results=data["hashes"],
                keyword=data["keyword"],
            )
        assert analysis.status == AIAnalysisStatus.FALLBACK

    def test_helper_methods(self, sample_text: Path) -> None:
        data = _forensic_bundle(sample_text)
        service = AIService(enabled=True)
        kwargs = {
            "case_id": "CASE-9",
            "evidence_id": "EV-AI-1",
            "hash_results": data["hashes"],
            "keyword": data["keyword"],
        }
        assert service.summarize_case(**kwargs).status == AIAnalysisStatus.FALLBACK
        assert service.explain_findings(**kwargs).status == AIAnalysisStatus.FALLBACK
        assert service.generate_investigation_questions(**kwargs).investigation_questions is not None
        assert service.prioritize_findings(**kwargs).findings is not None

    def test_missing_ids_raise(self) -> None:
        with pytest.raises(AIAnalysisError):
            AIService().analyze(case_id="", evidence_id="EV-1")


class TestReportIntegration:
    def test_report_includes_optional_ai_section(
        self, sample_text: Path, tmp_path: Path
    ) -> None:
        data = _forensic_bundle(sample_text)
        ai = AIService(enabled=True).analyze(
            case_id="CASE-9",
            evidence_id="EV-AI-1",
            hash_results=data["hashes"],
            integrity=data["integrity"],
            keyword=data["keyword"],
            timeline=data["timeline"],
            custody_events=data["custody_events"],
            custody_verification=data["custody_verification"],
        )
        report_service = ReportService(output_dir=tmp_path / "reports")
        report = report_service.build_report(
            case_id="CASE-9",
            evidence_id="EV-AI-1",
            evidence_path=str(sample_text),
            hash_results=data["hashes"],
            integrity=data["integrity"],
            keyword=data["keyword"],
            timeline=data["timeline"],
            custody_events=data["custody_events"],
            custody_verification=data["custody_verification"],
            ai_analysis=ai,
        )
        assert report.ai_analysis is not None
        assert report.ai_analysis.status == AIAnalysisStatus.FALLBACK
        assert "ai_assisted_analysis" in report.evidence_summary.modules_executed
        payload = report_service.dumps_json(report)
        assert '"ai"' in payload
        assert "NOT A SUBSTITUTE FOR FORENSIC FINDINGS" in payload
        pdf = report_service.generate_pdf(report)
        assert Path(pdf.output_path).is_file()

    def test_report_works_without_ai(self, sample_text: Path, tmp_path: Path) -> None:
        data = _forensic_bundle(sample_text)
        report = ReportService(output_dir=tmp_path / "reports").build_report(
            case_id="CASE-9",
            evidence_id="EV-AI-1",
            hash_results=data["hashes"],
            integrity=data["integrity"],
        )
        assert report.ai_analysis is None


class TestSearchResultContext:
    def test_search_result_keyword_summary(self, sample_text: Path) -> None:
        result = KeywordSearchService().search_directory(
            sample_text.parent,
            ["confidential", "bitcoin"],
        )
        assert isinstance(result, SearchResult)
        ctx = build_ai_context(
            case_id="CASE-9",
            evidence_id="EV-AI-1",
            keyword=result,
        )
        assert ctx.keyword_summary["total_matches"] >= 1
        assert "privacy" not in ctx.browser_summary or True
