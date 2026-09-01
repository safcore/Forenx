"""Pydantic schemas for forensic browser artifact analysis."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class BrowserStatus(str, Enum):
    """Outcome status for a browser analysis operation."""

    SUCCESS = "success"
    PARTIAL = "partial"
    EMPTY = "empty"
    ERROR = "error"


class BrowserVisit(BaseModel):
    """A browsing history visit record."""

    browser: str
    profile_name: str | None = None
    url: str
    title: str | None = None
    visit_count: int | None = None
    visit_time: datetime | None = None
    transition_type: str | None = None
    search_engine: str | None = None
    search_query: str | None = None
    domain: str | None = None


class BrowserDownload(BaseModel):
    """A browser download artifact."""

    browser: str
    profile_name: str | None = None
    source_url: str | None = None
    local_path: str | None = None
    downloaded_time: datetime | None = None
    file_size: int | None = None
    danger_status: str | None = None


class BrowserBookmark(BaseModel):
    """A browser bookmark entry."""

    browser: str
    profile_name: str | None = None
    title: str | None = None
    url: str | None = None
    created_time: datetime | None = None
    folder: str | None = None


class BrowserCookieMetadata(BaseModel):
    """Cookie metadata without sensitive values."""

    browser: str
    profile_name: str | None = None
    host: str | None = None
    name: str | None = None
    creation_time: datetime | None = None
    last_access_time: datetime | None = None
    expiration_time: datetime | None = None
    secure: bool | None = None
    http_only: bool | None = None


class BrowserSearch(BaseModel):
    """A detected search-engine query from history."""

    browser: str
    profile_name: str | None = None
    engine: str
    search_query: str
    visit_time: datetime | None = None
    url: str | None = None


class BrowserLoginPage(BaseModel):
    """A URL likely representing a login / authentication page."""

    browser: str
    profile_name: str | None = None
    url: str
    visit_time: datetime | None = None
    title: str | None = None


class BrowserSummary(BaseModel):
    """Aggregate counts for a browser analysis run."""

    browser: str | None = None
    profile_name: str | None = None
    history_count: int = Field(ge=0, default=0)
    download_count: int = Field(ge=0, default=0)
    bookmark_count: int = Field(ge=0, default=0)
    cookie_count: int = Field(ge=0, default=0)
    search_count: int = Field(ge=0, default=0)
    login_page_count: int = Field(ge=0, default=0)
    execution_time_ms: float = Field(ge=0, default=0)
    timestamp: datetime
    status: BrowserStatus
    message: str


class BrowserArtifacts(BaseModel):
    """Typed intermediate artifact collection shared by browser extractors.

    Used internally by Chrome/Edge/Firefox analyzers before the dispatcher
    wraps the data into a full ``BrowserResult``.
    """

    browser: str
    profile_name: str | None = None
    history: list[BrowserVisit] = Field(default_factory=list)
    downloads: list[BrowserDownload] = Field(default_factory=list)
    bookmarks: list[BrowserBookmark] = Field(default_factory=list)
    cookies: list[BrowserCookieMetadata] = Field(default_factory=list)
    searches: list[BrowserSearch] = Field(default_factory=list)
    login_pages: list[BrowserLoginPage] = Field(default_factory=list)


class BrowserResult(BaseModel):
    """Complete browser artifact extraction result for one profile."""

    browser: str
    profile_name: str | None = None
    profile_path: str
    status: BrowserStatus
    message: str
    timestamp: datetime
    execution_time_ms: float = Field(ge=0, default=0)
    history: list[BrowserVisit] = Field(default_factory=list)
    downloads: list[BrowserDownload] = Field(default_factory=list)
    bookmarks: list[BrowserBookmark] = Field(default_factory=list)
    cookies: list[BrowserCookieMetadata] = Field(default_factory=list)
    searches: list[BrowserSearch] = Field(default_factory=list)
    login_pages: list[BrowserLoginPage] = Field(default_factory=list)
    summary: BrowserSummary
