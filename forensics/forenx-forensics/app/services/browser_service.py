"""Browser analysis service orchestration for the ForenX forensics engine.

Provides the public Phase 5 API for offline Chrome / Edge / Firefox profile
analysis (history, downloads, bookmarks, cookie metadata, searches, logins).

Typical usage example:

    from app.services.browser_service import BrowserService

    result = BrowserService().analyze_browser("evidence/sample_case/browser/chrome/Default")
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.browser.dispatcher import analyze_profile, detect_browser_type, discover_profiles
from app.browser.models import BrowserType
from app.schemas.browser import (
    BrowserBookmark,
    BrowserCookieMetadata,
    BrowserDownload,
    BrowserLoginPage,
    BrowserResult,
    BrowserSearch,
    BrowserStatus,
    BrowserSummary,
    BrowserVisit,
)
from app.utils.exceptions import EvidenceFileError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BrowserService:
    """High-level API for offline browser artifact analysis.

    Designed for reuse by CLI tools, tests, and a future Django backend.
    """

    def __init__(self) -> None:
        """Initialize the browser analysis service."""

    def analyze_browser(
        self,
        profile_dir: str | Path,
        *,
        browser: str | BrowserType | None = None,
        profile_name: str | None = None,
    ) -> BrowserResult:
        """Analyze a single browser profile directory.

        Args:
            profile_dir: Path to a Chrome/Edge/Firefox profile directory.
            browser: Optional explicit browser override.
            profile_name: Optional profile label override.

        Returns:
            ``BrowserResult`` containing all extracted artifact collections.
        """
        logger.info(
            "BrowserService.analyze_browser started profile=%s",
            Path(profile_dir).name if profile_dir else "",
        )
        result = analyze_profile(
            profile_dir,
            browser=browser,
            profile_name=profile_name,
        )
        logger.info(
            "BrowserService.analyze_browser finished browser=%s status=%s",
            result.browser,
            result.status.value,
        )
        return result

    def analyze_directory(self, directory: str | Path) -> list[BrowserResult]:
        """Discover and analyze browser profiles under a directory tree.

        Args:
            directory: Root directory containing one or more profiles.

        Returns:
            List of ``BrowserResult`` objects (empty when none found).
        """
        root = Path(directory)
        if not str(directory).strip():
            raise EvidenceFileError("Browser evidence directory path must not be empty")
        logger.info("BrowserService.analyze_directory started dir=%s", root)
        profiles = discover_profiles(root)
        results = [
            analyze_profile(path, browser=browser)
            for path, browser in profiles
        ]
        logger.info(
            "BrowserService.analyze_directory finished profiles=%d",
            len(results),
        )
        return results

    def extract_history(self, profile_dir: str | Path) -> list[BrowserVisit]:
        """Extract browsing history from a profile directory."""
        return self.analyze_browser(profile_dir).history

    def extract_downloads(self, profile_dir: str | Path) -> list[BrowserDownload]:
        """Extract download artifacts from a profile directory."""
        return self.analyze_browser(profile_dir).downloads

    def extract_bookmarks(self, profile_dir: str | Path) -> list[BrowserBookmark]:
        """Extract bookmarks from a profile directory."""
        return self.analyze_browser(profile_dir).bookmarks

    def extract_cookies(self, profile_dir: str | Path) -> list[BrowserCookieMetadata]:
        """Extract cookie metadata (never values) from a profile directory."""
        return self.analyze_browser(profile_dir).cookies

    def extract_searches(self, profile_dir: str | Path) -> list[BrowserSearch]:
        """Extract detected search-engine queries from history."""
        return self.analyze_browser(profile_dir).searches

    def extract_login_pages(self, profile_dir: str | Path) -> list[BrowserLoginPage]:
        """Extract likely login/auth page visits from history."""
        return self.analyze_browser(profile_dir).login_pages

    def summarize(
        self,
        results: BrowserResult | list[BrowserResult],
    ) -> BrowserSummary:
        """Summarize one or more browser analysis results.

        Args:
            results: A single result or list of results.

        Returns:
            Aggregated ``BrowserSummary``.
        """
        items = results if isinstance(results, list) else [results]
        if not items:
            return BrowserSummary(
                browser=None,
                profile_name=None,
                timestamp=datetime.now(timezone.utc),
                status=BrowserStatus.EMPTY,
                message="No browser results to summarize",
            )

        history_count = sum(item.summary.history_count for item in items)
        download_count = sum(item.summary.download_count for item in items)
        bookmark_count = sum(item.summary.bookmark_count for item in items)
        cookie_count = sum(item.summary.cookie_count for item in items)
        search_count = sum(item.summary.search_count for item in items)
        login_page_count = sum(item.summary.login_page_count for item in items)
        execution_time_ms = round(sum(item.execution_time_ms for item in items), 3)

        browsers = {item.browser for item in items}
        browser_label = next(iter(browsers)) if len(browsers) == 1 else "Multiple"
        profile_names = {item.profile_name for item in items if item.profile_name}
        profile_label = (
            next(iter(profile_names)) if len(profile_names) == 1 else None
        )

        total = (
            history_count
            + download_count
            + bookmark_count
            + cookie_count
            + search_count
            + login_page_count
        )
        status = BrowserStatus.SUCCESS if total else BrowserStatus.EMPTY
        message = (
            f"Summarized {len(items)} browser profile(s) with {total} artifact(s)"
        )
        return BrowserSummary(
            browser=browser_label,
            profile_name=profile_label,
            history_count=history_count,
            download_count=download_count,
            bookmark_count=bookmark_count,
            cookie_count=cookie_count,
            search_count=search_count,
            login_page_count=login_page_count,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.now(timezone.utc),
            status=status,
            message=message,
        )

    def detect_browser(self, profile_dir: str | Path) -> str:
        """Detect the browser type for a profile directory."""
        return detect_browser_type(Path(profile_dir)).value
