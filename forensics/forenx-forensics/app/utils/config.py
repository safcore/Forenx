"""Centralized configuration for the ForenX forensics engine.

All path and capability constants used across modules are defined here
so they can be imported consistently and overridden in later phases
(e.g. via environment variables or Django settings).
"""

from __future__ import annotations

import os
from importlib import metadata
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (resolved relative to the package root)
# ---------------------------------------------------------------------------

BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
VERSION_FILE: Path = BASE_DIR / "VERSION"
LOG_DIRECTORY: Path = BASE_DIR / "logs"
OUTPUTS_DIRECTORY: Path = BASE_DIR / "outputs"
EVIDENCE_DIRECTORY: Path = BASE_DIR / "evidence"
ASSETS_DIRECTORY: Path = BASE_DIR / "assets"

# Log file names (created automatically by the logging subsystem)
APPLICATION_LOG_FILE: str = "application.log"
ERRORS_LOG_FILE: str = "errors.log"

# Logging rotation
LOG_MAX_BYTES: int = 5 * 1024 * 1024  # 5 MiB
LOG_BACKUP_COUNT: int = 5


def _read_version(version_file: Path = VERSION_FILE) -> str:
    """Read the project version from VERSION or installed package metadata.

    Args:
        version_file: Path to the VERSION file at the project root.

    Returns:
        Version string stripped of surrounding whitespace.

    Raises:
        FileNotFoundError: If no VERSION file or installed package metadata exists.
        ValueError: If the VERSION file is empty.
    """
    if version_file.is_file():
        version = version_file.read_text(encoding="utf-8").strip()
        if not version:
            raise ValueError(f"VERSION file is empty: {version_file}")
        return version

    try:
        return metadata.version("forenx-forensics")
    except metadata.PackageNotFoundError as exc:
        raise FileNotFoundError(
            f"VERSION file not found: {version_file} and package metadata unavailable"
        ) from exc


# ---------------------------------------------------------------------------
# Project identity
# ---------------------------------------------------------------------------

PROJECT_NAME: str = "ForenX Forensics Engine"
PROJECT_VERSION: str = _read_version()

# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

HASH_CHUNK_SIZE: int = 8 * 1024 * 1024  # 8 MiB; stream large evidence files
SUPPORTED_HASH_ALGORITHMS: frozenset[str] = frozenset({"md5", "sha1", "sha256"})

# ---------------------------------------------------------------------------
# Keyword search
# ---------------------------------------------------------------------------

KEYWORD_CONTEXT_CHARS: int = 20
KEYWORD_BINARY_PROBE_BYTES: int = 8192

# ---------------------------------------------------------------------------
# Supported file types (currently implemented capabilities)
# ---------------------------------------------------------------------------

SUPPORTED_IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"}
)

SUPPORTED_PDF_EXTENSIONS: frozenset[str] = frozenset({".pdf"})

SUPPORTED_DOCUMENT_EXTENSIONS: frozenset[str] = frozenset({".docx"})

SUPPORTED_TEXT_EXTENSIONS: frozenset[str] = frozenset(
    {".txt", ".log", ".csv", ".json", ".xml"}
)

# ---------------------------------------------------------------------------
# Supported browsers (currently implemented offline analyzers)
# ---------------------------------------------------------------------------

SUPPORTED_BROWSER_NAMES: frozenset[str] = frozenset(
    {
        "chrome",
        "edge",
        "firefox",
    }
)

# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

REPORTS_DIRECTORY: Path = OUTPUTS_DIRECTORY / "reports"
REPORT_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# AI-assisted investigation (Phase 9) — local-first, offline-compatible
# ---------------------------------------------------------------------------


def _env_bool(name: str, default: bool) -> bool:
    """Parse a boolean environment variable."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _env_str(name: str, default: str) -> str:
    """Parse a string environment variable."""
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip()


def _env_int(name: str, default: int) -> int:
    """Parse an integer environment variable."""
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        return default


# Defaults keep AI off unless explicitly enabled by the host application.
FORENX_AI_ENABLED: bool = _env_bool("FORENX_AI_ENABLED", False)
FORENX_AI_PROVIDER: str = _env_str("FORENX_AI_PROVIDER", "local").lower()
FORENX_AI_MODEL: str = _env_str("FORENX_AI_MODEL", "deterministic-local")
FORENX_AI_ALLOW_NETWORK: bool = _env_bool("FORENX_AI_ALLOW_NETWORK", False)

# Deterministic context bounds (prevent unbounded prompts / memory use).
AI_MAX_KEYWORD_MATCHES: int = _env_int("FORENX_AI_MAX_KEYWORD_MATCHES", 25)
AI_MAX_TIMELINE_EVENTS: int = _env_int("FORENX_AI_MAX_TIMELINE_EVENTS", 40)
AI_MAX_BROWSER_ITEMS: int = _env_int("FORENX_AI_MAX_BROWSER_ITEMS", 20)
AI_MAX_STRING_CHARS: int = _env_int("FORENX_AI_MAX_STRING_CHARS", 500)
AI_MAX_CUSTODY_EVENTS: int = _env_int("FORENX_AI_MAX_CUSTODY_EVENTS", 25)

# ---------------------------------------------------------------------------
# Required directories verified at startup
# ---------------------------------------------------------------------------

REQUIRED_DIRECTORIES: tuple[Path, ...] = (
    LOG_DIRECTORY,
    OUTPUTS_DIRECTORY,
    OUTPUTS_DIRECTORY / "hashes",
    OUTPUTS_DIRECTORY / "metadata",
    OUTPUTS_DIRECTORY / "reports",
    OUTPUTS_DIRECTORY / "timelines",
    EVIDENCE_DIRECTORY,
    EVIDENCE_DIRECTORY / "images",
    EVIDENCE_DIRECTORY / "documents",
    EVIDENCE_DIRECTORY / "browser",
    EVIDENCE_DIRECTORY / "logs",
    EVIDENCE_DIRECTORY / "sample_case",
    ASSETS_DIRECTORY,
    ASSETS_DIRECTORY / "logo",
    ASSETS_DIRECTORY / "icons",
    ASSETS_DIRECTORY / "report_templates",
)
