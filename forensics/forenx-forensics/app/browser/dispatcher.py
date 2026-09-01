"""Browser profile detection and analysis dispatcher."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from app.browser.chrome import analyze_chrome_profile
from app.browser.edge import analyze_edge_profile
from app.browser.firefox import analyze_firefox_profile
from app.browser.models import BrowserType
from app.schemas.browser import (
    BrowserArtifacts,
    BrowserResult,
    BrowserStatus,
    BrowserSummary,
)
from app.utils.exceptions import BrowserHistoryError, EvidenceFileError
from app.utils.logger import get_logger

logger = get_logger(__name__)


def detect_browser_type(profile_dir: Path) -> BrowserType:
    """Detect browser type from files present in a profile directory.

    Args:
        profile_dir: Candidate browser profile directory.

    Returns:
        Detected ``BrowserType``.

    Raises:
        EvidenceFileError: If the directory is missing.
        BrowserHistoryError: If the browser type cannot be determined.
    """
    if not profile_dir.exists():
        raise EvidenceFileError(f"Browser profile directory not found: {profile_dir}")
    if not profile_dir.is_dir():
        raise EvidenceFileError(f"Browser profile path is not a directory: {profile_dir}")

    path_text = str(profile_dir).lower()
    has_places = (profile_dir / "places.sqlite").is_file()
    has_history = (profile_dir / "History").is_file()
    has_bookmarks = (profile_dir / "Bookmarks").is_file()
    has_cookies = (profile_dir / "Cookies").is_file()

    if has_places:
        logger.info("Detected Firefox profile markers in '%s'", profile_dir)
        return BrowserType.FIREFOX

    if has_history or has_bookmarks or has_cookies:
        if "edge" in path_text or "microsoft" in path_text:
            logger.info("Detected Edge profile markers in '%s'", profile_dir)
            return BrowserType.EDGE
        if "chrome" in path_text or "google" in path_text:
            logger.info("Detected Chrome profile markers in '%s'", profile_dir)
            return BrowserType.CHROME
        # Default Chromium-like profiles without path hints to Chrome.
        logger.info(
            "Detected Chromium profile markers in '%s'; defaulting to Chrome",
            profile_dir,
        )
        return BrowserType.CHROME

    raise BrowserHistoryError(
        f"Unsupported or unrecognized browser profile directory: {profile_dir}"
    )


def _build_result(
    *,
    profile_dir: Path,
    artifacts: BrowserArtifacts,
    started: float,
) -> BrowserResult:
    """Build a ``BrowserResult`` from extractor output."""
    elapsed = round((time.perf_counter() - started) * 1000.0, 3)
    total = (
        len(artifacts.history)
        + len(artifacts.downloads)
        + len(artifacts.bookmarks)
        + len(artifacts.cookies)
        + len(artifacts.searches)
        + len(artifacts.login_pages)
    )

    expected_names = (
        ("History", "Bookmarks", "Cookies")
        if artifacts.browser in {BrowserType.CHROME.value, BrowserType.EDGE.value}
        else ("places.sqlite", "cookies.sqlite")
    )
    missing_expected = any(not (profile_dir / name).exists() for name in expected_names)

    if total == 0:
        status = BrowserStatus.EMPTY
        message = "No browser artifacts found"
    elif missing_expected:
        status = BrowserStatus.PARTIAL
        message = "Browser artifacts extracted with some source files missing"
    else:
        status = BrowserStatus.SUCCESS
        message = "Browser artifacts extracted successfully"

    timestamp = datetime.now(timezone.utc)
    summary = BrowserSummary(
        browser=artifacts.browser,
        profile_name=artifacts.profile_name,
        history_count=len(artifacts.history),
        download_count=len(artifacts.downloads),
        bookmark_count=len(artifacts.bookmarks),
        cookie_count=len(artifacts.cookies),
        search_count=len(artifacts.searches),
        login_page_count=len(artifacts.login_pages),
        execution_time_ms=elapsed,
        timestamp=timestamp,
        status=status,
        message=message,
    )
    return BrowserResult(
        browser=artifacts.browser,
        profile_name=artifacts.profile_name,
        profile_path=str(profile_dir.resolve()),
        status=status,
        message=message,
        timestamp=timestamp,
        execution_time_ms=elapsed,
        history=artifacts.history,
        downloads=artifacts.downloads,
        bookmarks=artifacts.bookmarks,
        cookies=artifacts.cookies,
        searches=artifacts.searches,
        login_pages=artifacts.login_pages,
        summary=summary,
    )


def analyze_profile(
    profile_dir: str | Path,
    *,
    browser: BrowserType | str | None = None,
    profile_name: str | None = None,
) -> BrowserResult:
    """Detect browser type (if needed) and analyze a profile directory.

    Args:
        profile_dir: Path to a browser profile directory.
        browser: Optional explicit browser override.
        profile_name: Optional profile label override.

    Returns:
        Structured ``BrowserResult``.
    """
    path = Path(profile_dir)
    started = time.perf_counter()
    logger.info("Browser analysis started for profile '%s'", path)

    if browser is None:
        detected = detect_browser_type(path)
    elif isinstance(browser, BrowserType):
        detected = browser
    else:
        detected = BrowserType(str(browser))

    logger.info("Browser selected: %s", detected.value)

    if detected is BrowserType.CHROME:
        artifacts = analyze_chrome_profile(path, profile_name=profile_name)
    elif detected is BrowserType.EDGE:
        artifacts = analyze_edge_profile(path, profile_name=profile_name)
    elif detected is BrowserType.FIREFOX:
        artifacts = analyze_firefox_profile(path, profile_name=profile_name)
    else:
        raise BrowserHistoryError(f"Unsupported browser: {detected}")

    result = _build_result(profile_dir=path, artifacts=artifacts, started=started)
    logger.info(
        "Browser analysis finished browser=%s history=%d downloads=%d "
        "bookmarks=%d cookies=%d searches=%d login_pages=%d time_ms=%.3f",
        result.browser,
        result.summary.history_count,
        result.summary.download_count,
        result.summary.bookmark_count,
        result.summary.cookie_count,
        result.summary.search_count,
        result.summary.login_page_count,
        result.execution_time_ms,
    )
    return result


def discover_profiles(root: Path) -> list[tuple[Path, BrowserType]]:
    """Discover likely browser profile directories under ``root``.

    Returns:
        List of ``(profile_path, detected_browser)`` tuples.
    """
    discovered: list[tuple[Path, BrowserType]] = []
    if not root.is_dir():
        raise EvidenceFileError(f"Browser evidence directory not found: {root}")

    candidates = [root, *root.rglob("*")]
    seen: set[Path] = set()
    for candidate in candidates:
        if not candidate.is_dir():
            continue
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        try:
            browser = detect_browser_type(candidate)
        except (BrowserHistoryError, EvidenceFileError):
            continue
        seen.add(resolved)
        discovered.append((candidate, browser))
    return discovered
