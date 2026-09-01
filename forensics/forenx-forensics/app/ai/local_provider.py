"""Deterministic offline AI provider (no network, no external model).

Produces useful assistive output labeled as DETERMINISTIC FALLBACK.
"""

from __future__ import annotations

from app.ai.models import make_analysis_id, utc_now
from app.ai.provider import AIProvider
from app.schemas.ai import (
    AIAnalysis,
    AIAnalysisStatus,
    AIConfidence,
    AIContextSummary,
    AIEvidenceRef,
    AIFinding,
    AIInvestigationQuestion,
    AIObservation,
    AIProviderType,
    AIRecommendation,
    AIStatementKind,
)
from app.utils.config import FORENX_AI_MODEL
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LocalDeterministicProvider(AIProvider):
    """Offline provider that derives assistive conclusions from structured context."""

    name = "local-deterministic"

    def analyze(
        self,
        context: AIContextSummary,
        instructions: str,
        *,
        prompt: str,
    ) -> AIAnalysis:
        """Build deterministic advisory analysis from context alone."""
        del instructions, prompt  # Prompt retained for interface parity / future LLMs.
        logger.info(
            "LocalDeterministicProvider.analyze case_id=%s evidence_id=%s",
            context.case_id,
            context.evidence_id,
        )

        observations: list[AIObservation] = []
        findings: list[AIFinding] = []
        recommendations: list[AIRecommendation] = []
        questions: list[AIInvestigationQuestion] = []
        supporting: list[AIEvidenceRef] = []
        limitations = list(context.limitations) + list(context.truncation_notes)
        limitations.append("DETERMINISTIC FALLBACK - not model-generated AI output")

        oid = 1
        if context.evidence_sha256:
            ref = AIEvidenceRef(
                source="hash",
                description="Evidence SHA-256 digest from deterministic hashing",
                extra={"sha256": context.evidence_sha256},
            )
            supporting.append(ref)
            observations.append(
                AIObservation(
                    observation_id=f"O-{oid:03d}",
                    kind=AIStatementKind.OBSERVED_FACT,
                    text=f"Evidence SHA-256 recorded as {context.evidence_sha256}",
                    supporting_evidence=[ref],
                    confidence=AIConfidence.HIGH,
                )
            )
            oid += 1

        if context.integrity_status:
            ref = AIEvidenceRef(
                source="hash",
                description=f"Integrity status={context.integrity_status}",
            )
            observations.append(
                AIObservation(
                    observation_id=f"O-{oid:03d}",
                    kind=AIStatementKind.OBSERVED_FACT,
                    text=f"Integrity status is {context.integrity_status}",
                    supporting_evidence=[ref],
                    confidence=AIConfidence.HIGH,
                )
            )
            oid += 1
            if context.integrity_status.upper() == "FAIL":
                findings.append(
                    AIFinding(
                        finding_id="AF-001",
                        title="Evidence integrity check failed",
                        kind=AIStatementKind.OBSERVED_FACT,
                        description=(
                            "Deterministic integrity verification reported FAIL for "
                            "the supplied evidence digest binding."
                        ),
                        priority=1,
                        confidence=AIConfidence.HIGH,
                        supporting_evidence=[ref],
                    )
                )

        if context.custody_valid is True:
            ref = AIEvidenceRef(
                source="custody",
                description="Custody chain verification reported valid",
            )
            observations.append(
                AIObservation(
                    observation_id=f"O-{oid:03d}",
                    kind=AIStatementKind.OBSERVED_FACT,
                    text="Custody chain verification is VALID",
                    supporting_evidence=[ref],
                    confidence=AIConfidence.HIGH,
                )
            )
            oid += 1
        elif context.custody_valid is False:
            broken = context.custody_summary.get("broken_event_id")
            ref = AIEvidenceRef(
                source="custody",
                description="Custody chain verification reported invalid",
                event_id=broken,
            )
            observations.append(
                AIObservation(
                    observation_id=f"O-{oid:03d}",
                    kind=AIStatementKind.OBSERVED_FACT,
                    text="Custody chain verification is INVALID",
                    supporting_evidence=[ref],
                    confidence=AIConfidence.HIGH,
                )
            )
            oid += 1
            findings.append(
                AIFinding(
                    finding_id="AF-002",
                    title="Custody chain verification failed",
                    kind=AIStatementKind.OBSERVED_FACT,
                    description=(
                        "Supplied custody verification indicates the hash chain is "
                        f"invalid (broken_event_id={broken or 'unknown'})."
                    ),
                    priority=1,
                    confidence=AIConfidence.HIGH,
                    supporting_evidence=[ref],
                )
            )

        keyword_summary = context.keyword_summary or {}
        total_matches = int(keyword_summary.get("total_matches") or 0)
        if total_matches:
            ref = AIEvidenceRef(
                source="keyword",
                description=f"{total_matches} keyword match(es) recorded",
            )
            observations.append(
                AIObservation(
                    observation_id=f"O-{oid:03d}",
                    kind=AIStatementKind.OBSERVED_FACT,
                    text=f"Keyword search recorded {total_matches} match(es)",
                    supporting_evidence=[ref],
                    confidence=AIConfidence.HIGH,
                )
            )
            oid += 1

        suspicious = dict(keyword_summary.get("suspicious_keyword_hits") or {})
        if suspicious:
            top = sorted(suspicious.items(), key=lambda item: (-item[1], item[0]))
            for keyword, count in top[:5]:
                ref = AIEvidenceRef(
                    source="keyword",
                    keyword=keyword,
                    description=f"Suspicious keyword '{keyword}' occurred {count} time(s)",
                )
                supporting.append(ref)
                findings.append(
                    AIFinding(
                        finding_id=f"AF-K-{keyword}",
                        title=f"Suspicious keyword indicator: {keyword}",
                        kind=AIStatementKind.INFERENCE,
                        description=(
                            f"The keyword '{keyword}' appears {count} time(s) in "
                            "deterministic keyword results. This is an investigative "
                            "indicator, not proof of wrongdoing."
                        ),
                        priority=3,
                        confidence=AIConfidence.MEDIUM,
                        supporting_evidence=[ref],
                        speculative=True,
                    )
                )
            recommendations.append(
                AIRecommendation(
                    recommendation_id="AR-001",
                    text=(
                        "Review files containing suspicious keyword hits and capture "
                        "additional surrounding context for analyst review."
                    ),
                    rationale="Suspicious keyword frequency was observed in deterministic search results.",
                    supporting_evidence=supporting[-min(3, len(supporting)) :],
                    priority=3,
                )
            )
            questions.append(
                AIInvestigationQuestion(
                    question_id="AQ-001",
                    question=(
                        "Which custodians or processes introduced the documents "
                        "containing the suspicious keywords?"
                    ),
                    rationale="Keyword indicators warrant timeline and custody correlation.",
                    supporting_evidence=supporting[-min(3, len(supporting)) :],
                )
            )

        browser = context.browser_summary or {}
        if browser:
            history = int(browser.get("history_count") or 0)
            downloads = int(browser.get("download_count") or 0)
            searches = int(browser.get("search_count") or 0)
            ref = AIEvidenceRef(
                source="browser",
                description=(
                    f"Browser artifacts: history={history}, downloads={downloads}, "
                    f"searches={searches}"
                ),
            )
            observations.append(
                AIObservation(
                    observation_id=f"O-{oid:03d}",
                    kind=AIStatementKind.OBSERVED_FACT,
                    text=ref.description,
                    supporting_evidence=[ref],
                    confidence=AIConfidence.HIGH,
                )
            )
            oid += 1
            if downloads or searches:
                findings.append(
                    AIFinding(
                        finding_id="AF-003",
                        title="Browser activity volume observed",
                        kind=AIStatementKind.INFERENCE,
                        description=(
                            "Browser downloads/searches are present and may warrant "
                            "correlation with keyword and timeline activity."
                        ),
                        priority=4,
                        confidence=AIConfidence.MEDIUM,
                        supporting_evidence=[ref],
                        speculative=True,
                    )
                )
                questions.append(
                    AIInvestigationQuestion(
                        question_id="AQ-002",
                        question=(
                            "Do browser download timestamps align with file creation "
                            "or modification events on the timeline?"
                        ),
                        rationale="Temporal correlation can clarify acquisition pathways.",
                        supporting_evidence=[ref],
                    )
                )

        timeline = context.timeline_summary or {}
        total_events = int(timeline.get("total_events") or 0)
        if total_events:
            ref = AIEvidenceRef(
                source="timeline",
                description=f"Timeline contains {total_events} event(s)",
            )
            observations.append(
                AIObservation(
                    observation_id=f"O-{oid:03d}",
                    kind=AIStatementKind.OBSERVED_FACT,
                    text=ref.description,
                    supporting_evidence=[ref],
                    confidence=AIConfidence.HIGH,
                )
            )
            oid += 1
            if total_events >= 20:
                findings.append(
                    AIFinding(
                        finding_id="AF-004",
                        title="Dense timeline activity",
                        kind=AIStatementKind.INFERENCE,
                        description=(
                            "A relatively dense timeline was reconstructed. Prioritize "
                            "clusters around keyword and browser artifacts."
                        ),
                        priority=5,
                        confidence=AIConfidence.LOW,
                        supporting_evidence=[ref],
                        speculative=True,
                    )
                )

        if not findings and not observations:
            limitations.append("Insufficient forensic context for detailed assistive analysis")
            summary = (
                "Insufficient deterministic forensic context was supplied for a rich "
                "assistive analysis."
            )
            confidence = AIConfidence.LOW
        else:
            summary = (
                "DETERMINISTIC FALLBACK analysis summarizes integrity, custody, "
                f"keyword matches ({total_matches}), browser activity, and "
                f"timeline volume ({total_events}). "
                "All inferences are advisory and do not replace forensic findings."
            )
            confidence = AIConfidence.MEDIUM if findings else AIConfidence.HIGH

        # Preserve custody/hash facts without reinterpretation.
        provenance = {
            "provider": self.name,
            "mode": "DETERMINISTIC_FALLBACK",
            "modules_present": list(context.modules_present),
            "evidence_sha256": context.evidence_sha256,
            "custody_valid": context.custody_valid,
            "integrity_status": context.integrity_status,
            "advisory_only": True,
        }

        return AIAnalysis(
            analysis_id=make_analysis_id(),
            case_id=context.case_id,
            evidence_id=context.evidence_id,
            generated_at=utc_now(),
            provider=AIProviderType.DETERMINISTIC,
            model=FORENX_AI_MODEL or "deterministic-local",
            status=AIAnalysisStatus.FALLBACK,
            confidence=confidence,
            summary=summary,
            observations=observations,
            findings=sorted(findings, key=lambda item: (item.priority, item.finding_id)),
            recommendations=recommendations,
            investigation_questions=questions,
            supporting_evidence=supporting,
            limitations=limitations,
            provenance=provenance,
        )


class UnavailableAIProvider(AIProvider):
    """Provider used when AI is disabled or network remote providers are blocked."""

    name = "unavailable"

    def __init__(self, *, reason: str) -> None:
        self.reason = reason

    def analyze(
        self,
        context: AIContextSummary,
        instructions: str,
        *,
        prompt: str,
    ) -> AIAnalysis:
        del instructions, prompt
        return AIAnalysis(
            analysis_id=make_analysis_id(),
            case_id=context.case_id,
            evidence_id=context.evidence_id,
            generated_at=utc_now(),
            provider=AIProviderType.UNAVAILABLE,
            model="none",
            status=AIAnalysisStatus.UNAVAILABLE,
            confidence=AIConfidence.UNKNOWN,
            summary=f"AI analysis unavailable: {self.reason}",
            limitations=[self.reason, "No external AI network call was performed"],
            provenance={
                "provider": self.name,
                "reason": self.reason,
                "advisory_only": True,
            },
        )
