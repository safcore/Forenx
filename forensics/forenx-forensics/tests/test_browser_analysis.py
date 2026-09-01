"""Comprehensive tests for Phase 5 browser analysis."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.services.browser_service import BrowserService
from app.utils.exceptions import BrowserHistoryError, EvidenceFileError
from tests.browser_fixtures import build_chromium_profile, build_firefox_profile


@pytest.fixture
def service(browser_service: BrowserService) -> BrowserService:
    """Alias browser_service for local readability."""
    return browser_service


class TestChromeArtifacts:
    """Chrome extractor tests."""

    def test_chrome_history(self, service: BrowserService, chrome_profile: Path) -> None:
        """Chrome history records are extracted with domains and times."""
        history = service.extract_history(chrome_profile)
        assert len(history) >= 12
        assert any(item.domain == "drive.google.com" for item in history)
        assert all(item.browser == "Chrome" for item in history)

    def test_chrome_downloads(self, service: BrowserService, chrome_profile: Path) -> None:
        """Chrome downloads include source URL and local path."""
        downloads = service.extract_downloads(chrome_profile)
        assert len(downloads) == 3
        assert downloads[0].source_url
        assert downloads[0].local_path
        assert downloads[0].file_size is not None

    def test_chrome_bookmarks(self, service: BrowserService, chrome_profile: Path) -> None:
        """Chrome bookmarks are parsed from JSON."""
        bookmarks = service.extract_bookmarks(chrome_profile)
        assert len(bookmarks) == 5
        assert any(item.title == "GitHub" for item in bookmarks)

    def test_chrome_cookies_metadata_only(
        self,
        service: BrowserService,
        chrome_profile: Path,
    ) -> None:
        """Cookie extraction never returns values."""
        cookies = service.extract_cookies(chrome_profile)
        assert len(cookies) == 18
        payload = [item.model_dump() for item in cookies]
        assert all("value" not in item for item in payload)
        assert all(item.name for item in cookies)


class TestEdgeAndFirefox:
    """Edge and Firefox extractor tests."""

    def test_edge_history(self, service: BrowserService, edge_profile: Path) -> None:
        """Edge profiles are detected and labeled correctly."""
        result = service.analyze_browser(edge_profile)
        assert result.browser == "Edge"
        assert result.summary.history_count >= 12

    def test_firefox_history(self, service: BrowserService, firefox_profile: Path) -> None:
        """Firefox places.sqlite history is extracted."""
        history = service.extract_history(firefox_profile)
        assert len(history) >= 5
        assert all(item.browser == "Firefox" for item in history)


class TestDerivedArtifacts:
    """Search and login-page derivation tests."""

    def test_search_extraction(self, service: BrowserService, chrome_profile: Path) -> None:
        """Search engine queries are derived from history URLs."""
        searches = service.extract_searches(chrome_profile)
        assert len(searches) == 5
        engines = {item.engine for item in searches}
        assert {"Google", "Bing", "DuckDuckGo", "Yahoo", "Brave"} <= engines
        assert any("confidential" in item.search_query.lower() for item in searches)

    def test_login_page_detection(
        self,
        service: BrowserService,
        chrome_profile: Path,
    ) -> None:
        """Login-like URLs are classified as login pages."""
        pages = service.extract_login_pages(chrome_profile)
        assert len(pages) >= 2
        assert any("accounts.google.com" in item.url for item in pages)
        assert any("login.microsoftonline.com" in item.url for item in pages)


class TestErrorHandlingAndSummary:
    """Error, empty, directory, and summary tests."""

    def test_missing_database(self, service: BrowserService, tmp_path: Path) -> None:
        """Missing profile directory raises EvidenceFileError."""
        with pytest.raises(EvidenceFileError):
            service.analyze_browser(tmp_path / "missing-profile")

    def test_unsupported_browser_dir(self, service: BrowserService, tmp_path: Path) -> None:
        """Directories without browser markers raise BrowserHistoryError."""
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(BrowserHistoryError):
            service.analyze_browser(empty)

    def test_corrupted_database(self, service: BrowserService, tmp_path: Path) -> None:
        """Corrupted History database raises BrowserHistoryError."""
        profile = tmp_path / "Chrome" / "Default"
        profile.mkdir(parents=True)
        (profile / "History").write_bytes(b"not a sqlite database")
        with pytest.raises(BrowserHistoryError):
            service.extract_history(profile)

    def test_empty_database(self, service: BrowserService, tmp_path: Path) -> None:
        """Valid empty History DB returns empty collections."""
        profile = tmp_path / "Chrome" / "Default"
        profile.mkdir(parents=True)
        conn = sqlite3.connect(profile / "History")
        conn.execute(
            "CREATE TABLE urls (id INTEGER PRIMARY KEY, url TEXT, title TEXT, "
            "visit_count INTEGER, last_visit_time INTEGER, hidden INTEGER DEFAULT 0)"
        )
        conn.execute(
            "CREATE TABLE visits (id INTEGER PRIMARY KEY, url INTEGER, visit_time INTEGER, "
            "transition INTEGER)"
        )
        conn.commit()
        conn.close()
        (profile / "Bookmarks").write_text(
            '{"roots":{"bookmark_bar":{"children":[],"type":"folder","name":"Bookmarks bar"},'
            '"other":{"children":[],"type":"folder","name":"Other"},'
            '"synced":{"children":[],"type":"folder","name":"Synced"}},"version":1}',
            encoding="utf-8",
        )
        result = service.analyze_browser(profile)
        assert result.summary.history_count == 0
        assert result.summary.download_count == 0

    def test_locked_database_handled_via_copy(
        self,
        service: BrowserService,
        chrome_profile: Path,
    ) -> None:
        """Analysis succeeds using a temporary copy of the evidence DB."""
        # Hold an open connection on the original DB, similar to a browser lock.
        lock = sqlite3.connect(chrome_profile / "History")
        try:
            result = service.analyze_browser(chrome_profile)
            assert result.summary.history_count >= 1
        finally:
            lock.close()

    def test_directory_analysis(
        self,
        service: BrowserService,
        tmp_path: Path,
    ) -> None:
        """analyze_directory discovers Chrome and Firefox profiles."""
        build_chromium_profile(tmp_path / "browser" / "chrome" / "Default")
        build_firefox_profile(tmp_path / "browser" / "firefox" / "abcd.default")
        results = service.analyze_directory(tmp_path / "browser")
        browsers = {item.browser for item in results}
        assert "Chrome" in browsers
        assert "Firefox" in browsers

    def test_summary_generation(
        self,
        service: BrowserService,
        chrome_profile: Path,
        firefox_profile: Path,
    ) -> None:
        """summarize aggregates multiple profile results."""
        results = [
            service.analyze_browser(chrome_profile),
            service.analyze_browser(firefox_profile),
        ]
        summary = service.summarize(results)
        assert summary.history_count >= 12
        assert summary.download_count >= 3
        assert summary.bookmark_count >= 5
        assert summary.cookie_count >= 18
        assert summary.search_count >= 5
        assert summary.login_page_count >= 2
        assert summary.status.value in {"success", "empty", "partial"}
