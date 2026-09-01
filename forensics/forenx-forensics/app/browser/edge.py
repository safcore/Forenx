"""Microsoft Edge offline profile artifact extraction.

Edge is Chromium-based and reuses the Chrome parsers with browser labeling.
"""

from __future__ import annotations

from pathlib import Path

from app.browser.chrome import analyze_chromium_profile
from app.browser.models import BrowserType
from app.schemas.browser import BrowserArtifacts
from app.utils.exceptions import EvidenceFileError
from app.utils.logger import get_logger

logger = get_logger(__name__)


def analyze_edge_profile(
    profile_dir: Path,
    profile_name: str | None = None,
) -> BrowserArtifacts:
    """Analyze an Edge profile directory and return artifact collections.

    Args:
        profile_dir: Path to an Edge profile folder (for example ``Default``).
        profile_name: Optional profile label override.

    Returns:
        Typed ``BrowserArtifacts`` collection.
    """
    if not profile_dir.is_dir():
        raise EvidenceFileError(f"Browser profile directory not found: {profile_dir}")

    logger.info("Analyzing Edge profile at '%s'", profile_dir)
    return analyze_chromium_profile(
        profile_dir,
        browser=BrowserType.EDGE.value,
        profile_name=profile_name or profile_dir.name,
    )
