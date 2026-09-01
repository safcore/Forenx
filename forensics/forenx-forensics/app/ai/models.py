"""Shared helpers for AI-assisted investigation."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from app.reports.models import is_sensitive_key, sanitize_value
from app.utils.config import AI_MAX_STRING_CHARS

AI_EVENT_NAMESPACE = uuid.UUID("c3a1b8e4-7d92-4f15-9a6e-0b8d2f4c1e77")

_SUSPICIOUS_KEYWORDS = frozenset(
    {
        "confidential",
        "bitcoin",
        "malware",
        "ransomware",
        "password",
        "dropbox",
        "exfil",
        "tor",
        "wallet",
        "credential",
        "phishing",
    }
)


def utc_now() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(timezone.utc)


def make_analysis_id() -> str:
    """Generate a unique AI analysis identifier."""
    return str(uuid.uuid4())


def truncate_text(value: Any, *, limit: int = AI_MAX_STRING_CHARS) -> Any:
    """Deterministically truncate long strings for context bounds."""
    if not isinstance(value, str):
        return value
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)] + "..."


def sanitize_and_bound(value: Any, *, limit: int = AI_MAX_STRING_CHARS) -> Any:
    """Redact secrets and truncate strings recursively."""
    cleaned = sanitize_value(value)
    if isinstance(cleaned, dict):
        return {
            str(key): sanitize_and_bound(item, limit=limit)
            for key, item in cleaned.items()
            if not is_sensitive_key(str(key)) or cleaned.get(key) == "[REDACTED]"
        }
    if isinstance(cleaned, list):
        return [sanitize_and_bound(item, limit=limit) for item in cleaned]
    if isinstance(cleaned, str):
        # Extra pattern redaction for inline secrets in free text.
        redacted = cleaned
        redacted = re.sub(
            r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*\S+",
            r"\1=[REDACTED]",
            redacted,
        )
        return truncate_text(redacted, limit=limit)
    return cleaned


def suspicious_keyword_hits(frequency: dict[str, int]) -> dict[str, int]:
    """Return keyword frequency entries that match the suspicious lexicon."""
    hits: dict[str, int] = {}
    for key, count in sorted(frequency.items()):
        if key.lower() in _SUSPICIOUS_KEYWORDS and count > 0:
            hits[key] = count
    return hits
