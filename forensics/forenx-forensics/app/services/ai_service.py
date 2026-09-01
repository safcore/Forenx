"""AI-assisted investigation service orchestration for ForenX.

Provides the public Phase 9 API for optional, local-first assistive analysis
over already-computed forensic service results.

Typical usage example:

    from app.services.ai_service import AIService

    analysis = AIService().analyze(case_id="CASE-1", evidence_id="EV-1", ...)
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from pydantic import ValidationError

from app.ai.context_builder import build_ai_context
from app.ai.dispatcher import resolve_ai_provider
from app.ai.models import make_analysis_id, utc_now
from app.ai.prompt_builder import build_analysis_instructions, build_prompt
from app.schemas.ai import (
    AIAnalysis,
    AIAnalysisStatus,
    AIConfidence,
    AIProviderType,
)
from app.schemas.browser import BrowserResult
from app.schemas.custody import CustodyEvent, CustodyVerificationResult
from app.schemas.hash import HashResult, IntegrityResult
from app.schemas.keyword import KeywordResult, SearchResult
from app.schemas.metadata import MetadataResult
from app.schemas.report import Finding, ForensicReport, InvestigationNote
from app.schemas.timeline import TimelineResult
from app.utils.config import FORENX_AI_ENABLED, FORENX_AI_MODEL
from app.utils.exceptions import AIAnalysisError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AIService:
    """High-level API for assistive AI investigation features.

    Does not modify evidence, hashes, custody ledgers, or deterministic findings.
    Default configuration keeps AI disabled until the host enables it.
    """

    def __init__(
        self,
        *,
        enabled: bool | None = None,
        provider_name: str | None = None,
        allow_network: bool | None = None,
    ) -> None:
        """Initialize AI service with optional configuration overrides."""
        self._enabled_override = enabled
        self._provider_name = provider_name
        self._allow_network = allow_network

    def _is_enabled(self) -> bool:
        return FORENX_AI_ENABLED if self._enabled_override is None else self._enabled_override

    def build_context(
        self,
        *,
        case_id: str,
        evidence_id: str,
        **kwargs,
    ):
        """Build a sanitized AI context from forensic artifacts."""
        if not str(case_id).strip() or not str(evidence_id).strip():
            raise AIAnalysisError("case_id and evidence_id are required")
        return build_ai_context(case_id=case_id, evidence_id=evidence_id, **kwargs)

    def analyze(
        self,
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
        task: str = "full_analysis",
    ) -> AIAnalysis:
        """Run assistive analysis over supplied forensic results."""
        logger.info(
            "AIService.analyze started case_id=%s evidence_id=%s enabled=%s",
            case_id,
            evidence_id,
            self._is_enabled(),
        )
        context = self.build_context(
            case_id=case_id,
            evidence_id=evidence_id,
            evidence_path=evidence_path,
            original_filename=original_filename,
            evidence_sha256=evidence_sha256,
            hash_results=hash_results,
            integrity=integrity,
            metadata=metadata,
            keyword=keyword,
            browser=browser,
            timeline=timeline,
            custody_events=custody_events,
            custody_verification=custody_verification,
            findings=findings,
            investigation_notes=investigation_notes,
            limitations=limitations,
            generated_at=generated_at,
            report=report,
        )

        if not self._is_enabled():
            result = AIAnalysis(
                analysis_id=make_analysis_id(),
                case_id=context.case_id,
                evidence_id=context.evidence_id,
                generated_at=utc_now(),
                provider=AIProviderType.UNAVAILABLE,
                model="none",
                status=AIAnalysisStatus.DISABLED,
                confidence=AIConfidence.UNKNOWN,
                summary="AI assistance is disabled by configuration.",
                limitations=[
                    "FORENX_AI_ENABLED=false",
                    "Enable AI explicitly in the host environment to run assistive analysis",
                ],
                provenance={
                    "advisory_only": True,
                    "evidence_sha256": context.evidence_sha256,
                    "custody_valid": context.custody_valid,
                    "integrity_status": context.integrity_status,
                },
            )
            logger.info("AIService.analyze finished status=disabled")
            return result

        provider, reason = resolve_ai_provider(
            enabled=True,
            provider_name=self._provider_name,
            allow_network=self._allow_network,
        )
        instructions = build_analysis_instructions(task=task)
        prompt = build_prompt(context, task=task)
        try:
            analysis = provider.analyze(context, instructions, prompt=prompt)
            if not isinstance(analysis, AIAnalysis):
                analysis = AIAnalysis.model_validate(analysis)
        except (ValidationError, TypeError, ValueError) as exc:
            logger.warning("AI provider returned malformed output: %s", type(exc).__name__)
            return AIAnalysis(
                analysis_id=make_analysis_id(),
                case_id=context.case_id,
                evidence_id=context.evidence_id,
                generated_at=utc_now(),
                provider=AIProviderType.UNAVAILABLE,
                model="none",
                status=AIAnalysisStatus.ERROR,
                confidence=AIConfidence.UNKNOWN,
                summary="AI provider returned malformed output; assistive analysis aborted.",
                limitations=[
                    "Malformed provider output was rejected during schema validation",
                    "No evidence or custody records were modified",
                ],
                provenance={
                    "advisory_only": True,
                    "error": type(exc).__name__,
                    "evidence_sha256": context.evidence_sha256,
                    "custody_valid": context.custody_valid,
                },
            )
        analysis.provenance = {
            **dict(analysis.provenance),
            "selection_reason": reason,
            "model_config": FORENX_AI_MODEL,
            "advisory_only": True,
        }
        logger.info(
            "AIService.analyze finished status=%s provider=%s",
            analysis.status.value,
            analysis.provider.value,
        )
        return analysis

    def summarize_case(self, **kwargs) -> AIAnalysis:
        """Generate an analyst-oriented narrative summary."""
        return self.analyze(task="summarize", **kwargs)

    def explain_findings(self, **kwargs) -> AIAnalysis:
        """Explain deterministic findings with advisory context."""
        return self.analyze(task="explain", **kwargs)

    def generate_investigation_questions(self, **kwargs) -> AIAnalysis:
        """Generate follow-up investigation questions."""
        return self.analyze(task="questions", **kwargs)

    def prioritize_findings(self, **kwargs) -> AIAnalysis:
        """Prioritize findings using deterministic assistive heuristics."""
        return self.analyze(task="prioritize", **kwargs)
