"""AI provider abstraction for assistive forensic analysis."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.ai import AIAnalysis, AIContextSummary


class AIProvider(ABC):
    """Provider interface for AI-assisted forensic interpretation.

    Implementations must not modify evidence, hashes, or custody ledgers.
    """

    name: str = "base"

    @abstractmethod
    def analyze(
        self,
        context: AIContextSummary,
        instructions: str,
        *,
        prompt: str,
    ) -> AIAnalysis:
        """Analyze a sanitized forensic context and return structured output."""
