"""Pydantic schemas for AI-assisted forensic investigation (Phase 9).

AI output is advisory. It must never be treated as independent forensic evidence.
Statements are explicitly classified as observed facts, inferences, or recommendations.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AIProviderType(str, Enum):
    """Configured AI provider identifiers."""

    LOCAL = "local"
    DETERMINISTIC = "deterministic"
    UNAVAILABLE = "unavailable"
    REMOTE = "remote"


class AIAnalysisStatus(str, Enum):
    """Outcome of an AI-assisted analysis request."""

    SUCCESS = "success"
    FALLBACK = "fallback"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class AIStatementKind(str, Enum):
    """Classification separating observed facts from inference/advice."""

    OBSERVED_FACT = "observed_fact"
    INFERENCE = "inference"
    RECOMMENDATION = "recommendation"


class AIConfidence(str, Enum):
    """Coarse confidence band for assistive conclusions."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class AIEvidenceRef(BaseModel):
    """Deterministic forensic artifact referenced by an AI statement."""

    source: str
    description: str
    event_id: str | None = None
    source_file: str | None = None
    keyword: str | None = None
    path: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class AIObservation(BaseModel):
    """Neutral observation derived from supplied forensic context."""

    observation_id: str
    kind: AIStatementKind = AIStatementKind.OBSERVED_FACT
    text: str
    supporting_evidence: list[AIEvidenceRef] = Field(default_factory=list)
    confidence: AIConfidence = AIConfidence.MEDIUM


class AIFinding(BaseModel):
    """Assistive finding with explicit fact/inference classification."""

    finding_id: str
    title: str
    kind: AIStatementKind
    description: str
    priority: int = Field(ge=1, le=10, default=5)
    confidence: AIConfidence = AIConfidence.MEDIUM
    supporting_evidence: list[AIEvidenceRef] = Field(default_factory=list)
    speculative: bool = False


class AIRecommendation(BaseModel):
    """Investigative lead (not a forensic conclusion)."""

    recommendation_id: str
    text: str
    rationale: str = ""
    supporting_evidence: list[AIEvidenceRef] = Field(default_factory=list)
    priority: int = Field(ge=1, le=10, default=5)


class AIInvestigationQuestion(BaseModel):
    """Follow-up question for the human analyst."""

    question_id: str
    question: str
    rationale: str = ""
    supporting_evidence: list[AIEvidenceRef] = Field(default_factory=list)


class AIContextSummary(BaseModel):
    """Bounded, sanitized investigation context for AI/provider consumption."""

    case_id: str
    evidence_id: str
    generated_at: datetime
    evidence_sha256: str | None = None
    integrity_status: str | None = None
    custody_valid: bool | None = None
    modules_present: list[str] = Field(default_factory=list)
    evidence_summary: dict[str, Any] = Field(default_factory=dict)
    hash_summary: dict[str, Any] = Field(default_factory=dict)
    metadata_summary: dict[str, Any] = Field(default_factory=dict)
    keyword_summary: dict[str, Any] = Field(default_factory=dict)
    browser_summary: dict[str, Any] = Field(default_factory=dict)
    timeline_summary: dict[str, Any] = Field(default_factory=dict)
    custody_summary: dict[str, Any] = Field(default_factory=dict)
    findings_summary: list[dict[str, Any]] = Field(default_factory=list)
    notes_summary: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    truncation_notes: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)


class AIAnalysis(BaseModel):
    """Structured AI-assisted investigation result (advisory only)."""

    analysis_id: str
    case_id: str
    evidence_id: str
    generated_at: datetime
    provider: AIProviderType
    model: str
    status: AIAnalysisStatus
    confidence: AIConfidence = AIConfidence.UNKNOWN
    summary: str
    observations: list[AIObservation] = Field(default_factory=list)
    findings: list[AIFinding] = Field(default_factory=list)
    recommendations: list[AIRecommendation] = Field(default_factory=list)
    investigation_questions: list[AIInvestigationQuestion] = Field(default_factory=list)
    supporting_evidence: list[AIEvidenceRef] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = (
        "AI-ASSISTED ANALYSIS - NOT A SUBSTITUTE FOR FORENSIC FINDINGS. "
        "Inferences and recommendations are advisory only."
    )
