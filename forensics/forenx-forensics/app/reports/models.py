"""Internal helpers for forensic report generation.

Reports are **derived artifacts**. They must never modify source evidence.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.utils.config import OUTPUTS_DIRECTORY
from app.utils.exceptions import ReportError

REPORT_VERSION = "1.0"
REPORTS_OUTPUT_DIR: Path = OUTPUTS_DIRECTORY / "reports"

# Conservative key patterns that must not appear in report payloads.
_SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "cookie_value",
    "authorization",
    "private_key",
    "api_key",
    "session_id",
)

_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9._-]+")


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def make_report_id() -> str:
    """Generate a unique report identifier."""
    return str(uuid.uuid4())


def sanitize_id_component(value: str, *, field_name: str) -> str:
    """Sanitize an identifier for safe inclusion in output filenames.

    Raises:
        ReportError: If the value is empty or becomes empty after sanitization.
    """
    if value is None or not str(value).strip():
        raise ReportError(f"{field_name} must not be empty")
    text = str(value).strip().replace("\\", "/").split("/")[-1]
    text = _SAFE_ID_RE.sub("_", text).strip("._")
    if not text or text in {".", ".."}:
        raise ReportError(f"Invalid {field_name} for report filename: {value!r}")
    if ".." in text:
        raise ReportError(f"Path traversal rejected in {field_name}: {value!r}")
    return text


def resolve_report_output_path(
    *,
    case_id: str,
    evidence_id: str,
    output_format: str,
    output_dir: Path | None = None,
) -> Path:
    """Resolve a safe report path under the configured reports directory."""
    fmt = output_format.strip().lower().lstrip(".")
    if fmt not in {"json", "pdf"}:
        raise ReportError(f"Unsupported report output format: {output_format!r}")

    safe_case = sanitize_id_component(case_id, field_name="case_id")
    safe_evidence = sanitize_id_component(evidence_id, field_name="evidence_id")
    root = Path(output_dir).resolve() if output_dir is not None else REPORTS_OUTPUT_DIR.resolve()
    root.mkdir(parents=True, exist_ok=True)
    filename = f"forenx_report_{safe_case}_{safe_evidence}.{fmt}"
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ReportError("Invalid report filename components")
    path = (root / filename).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ReportError(f"Path traversal rejected for report output: {path}") from exc
    return path


def is_sensitive_key(key: str) -> bool:
    """Return True when a mapping key looks like a secret field."""
    lowered = str(key).lower()
    return any(fragment in lowered for fragment in _SENSITIVE_KEY_FRAGMENTS)


def sanitize_value(value: Any) -> Any:
    """Recursively remove sensitive keys from nested mappings/lists."""
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if is_sensitive_key(str(key)):
                cleaned[str(key)] = "[REDACTED]"
            else:
                cleaned[str(key)] = sanitize_value(item)
        return cleaned
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_value(item) for item in value]
    return value


def datetime_to_iso(value: datetime | None) -> str | None:
    """Serialize timezone-aware datetimes to UTC ISO-8601 with ``Z`` when possible."""
    if value is None:
        return None
    if value.tzinfo is None:
        raise ReportError("Report timestamps must be timezone-aware")
    text = value.astimezone(timezone.utc).isoformat()
    if text.endswith("+00:00"):
        return text[:-6] + "Z"
    return text
