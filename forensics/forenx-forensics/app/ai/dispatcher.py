"""Select an AI provider according to local-first configuration."""

from __future__ import annotations

from app.ai.local_provider import LocalDeterministicProvider, UnavailableAIProvider
from app.ai.provider import AIProvider
from app.utils.config import (
    FORENX_AI_ALLOW_NETWORK,
    FORENX_AI_ENABLED,
    FORENX_AI_PROVIDER,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def resolve_ai_provider(
    *,
    enabled: bool | None = None,
    provider_name: str | None = None,
    allow_network: bool | None = None,
) -> tuple[AIProvider, str]:
    """Resolve the active provider and a human-readable selection reason.

    Network-backed providers are never invoked unless explicitly allowed.
    Even then, this repository ships no live remote client implementation —
    remote selection falls back to an unavailable provider (no network I/O).
    """
    is_enabled = FORENX_AI_ENABLED if enabled is None else enabled
    name = (provider_name or FORENX_AI_PROVIDER or "local").strip().lower()
    network_ok = FORENX_AI_ALLOW_NETWORK if allow_network is None else allow_network

    if not is_enabled:
        reason = "FORENX_AI_ENABLED=false"
        logger.info("AI provider resolved to unavailable (%s)", reason)
        return UnavailableAIProvider(reason=reason), reason

    if name in {"local", "deterministic", "fallback"}:
        logger.info("AI provider resolved to local deterministic")
        return LocalDeterministicProvider(), "local-deterministic"

    if name in {"remote", "openai", "gemini", "anthropic", "ollama"}:
        if not network_ok:
            reason = (
                f"Provider '{name}' requires network but FORENX_AI_ALLOW_NETWORK=false"
            )
            logger.info("AI provider blocked from network: %s", reason)
            # Prefer useful offline fallback rather than empty unavailable output.
            return LocalDeterministicProvider(), f"fallback-due-to-network-block:{name}"
        reason = (
            f"Remote provider '{name}' is not implemented in this engine build; "
            "no network call was made"
        )
        logger.info(reason)
        return UnavailableAIProvider(reason=reason), reason

    reason = f"Unknown AI provider '{name}'"
    logger.info(reason)
    return UnavailableAIProvider(reason=reason), reason
