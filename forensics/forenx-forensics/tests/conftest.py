"""Shared pytest fixtures for the ForenX forensics engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.browser_service import BrowserService
from app.services.custody_service import CustodyService
from app.services.hash_service import HashService
from app.services.keyword_service import KeywordSearchService
from app.services.metadata_service import MetadataService
from app.services.report_service import ReportService
from app.services.timeline_service import TimelineService
from tests.browser_fixtures import build_chromium_profile, build_firefox_profile


@pytest.fixture
def hash_service() -> HashService:
    """Return a HashService instance."""
    return HashService()


@pytest.fixture
def metadata_service(hash_service: HashService) -> MetadataService:
    """Return a MetadataService with injected HashService."""
    return MetadataService(hash_service=hash_service)


@pytest.fixture
def keyword_service() -> KeywordSearchService:
    """Return a KeywordSearchService instance."""
    return KeywordSearchService()


@pytest.fixture
def browser_service() -> BrowserService:
    """Return a BrowserService instance."""
    return BrowserService()


@pytest.fixture
def timeline_service(
    browser_service: BrowserService,
    metadata_service: MetadataService,
) -> TimelineService:
    """Return a TimelineService with shared browser/metadata services."""
    return TimelineService(
        browser_service=browser_service,
        metadata_service=metadata_service,
    )


@pytest.fixture
def custody_service(hash_service: HashService) -> CustodyService:
    """Return an isolated CustodyService with injected HashService."""
    return CustodyService(hash_service=hash_service)


@pytest.fixture
def report_service(tmp_path: Path) -> ReportService:
    """Return a ReportService writing into a temporary reports directory."""
    return ReportService(output_dir=tmp_path / "reports")


@pytest.fixture
def chrome_profile(tmp_path: Path) -> Path:
    """Create a rich synthetic Chrome profile."""
    return build_chromium_profile(tmp_path / "Chrome" / "User Data" / "Default")


@pytest.fixture
def edge_profile(tmp_path: Path) -> Path:
    """Create a synthetic Edge profile."""
    return build_chromium_profile(
        tmp_path / "Microsoft" / "Edge" / "User Data" / "Default"
    )


@pytest.fixture
def firefox_profile(tmp_path: Path) -> Path:
    """Create a synthetic Firefox profile."""
    return build_firefox_profile(tmp_path / "Firefox" / "Profiles" / "abcd.default")
