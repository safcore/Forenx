"""Evidence path classification helpers for timeline dispatch."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from app.browser.dispatcher import detect_browser_type
from app.utils.config import (
    SUPPORTED_DOCUMENT_EXTENSIONS,
    SUPPORTED_IMAGE_EXTENSIONS,
    SUPPORTED_PDF_EXTENSIONS,
)
from app.utils.exceptions import BrowserHistoryError, EvidenceFileError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TimelineSourceKind(str, Enum):
    """High-level classification of an evidence path for timeline extractors."""

    FILE = "file"
    DIRECTORY = "directory"
    BROWSER_PROFILE = "browser_profile"
    MISSING = "missing"


def is_browser_profile_dir(path: Path) -> bool:
    """Return ``True`` when ``path`` looks like a supported browser profile."""
    if not path.is_dir():
        return False
    try:
        detect_browser_type(path)
    except (BrowserHistoryError, EvidenceFileError):
        return False
    return True


def has_metadata_timestamps(path: Path) -> bool:
    """Return whether ``path`` may carry embedded metadata timestamps."""
    suffix = path.suffix.lower()
    return suffix in (
        SUPPORTED_IMAGE_EXTENSIONS
        | SUPPORTED_PDF_EXTENSIONS
        | SUPPORTED_DOCUMENT_EXTENSIONS
    )


def classify_evidence_path(evidence_path: str | Path) -> TimelineSourceKind:
    """Classify an evidence path for timeline extraction.

    Args:
        evidence_path: File or directory path.

    Returns:
        ``TimelineSourceKind`` describing how the dispatcher should treat it.
    """
    if evidence_path is None or (
        isinstance(evidence_path, str) and not str(evidence_path).strip()
    ):
        return TimelineSourceKind.MISSING

    path = Path(evidence_path)
    if not path.exists():
        return TimelineSourceKind.MISSING
    if path.is_file():
        return TimelineSourceKind.FILE
    if path.is_dir():
        if is_browser_profile_dir(path):
            logger.info("Classified '%s' as browser profile", path)
            return TimelineSourceKind.BROWSER_PROFILE
        return TimelineSourceKind.DIRECTORY
    return TimelineSourceKind.MISSING
