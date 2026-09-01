"""Pydantic schemas for forensic keyword search results."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SearchStatus(str, Enum):
    """Outcome status for a keyword search operation."""

    SUCCESS = "success"
    NO_MATCHES = "no_matches"
    SKIPPED = "skipped"
    ERROR = "error"


class KeywordMatch(BaseModel):
    """A single keyword hit within an evidence file.

    Attributes:
        file_name: Basename of the evidence file.
        absolute_path: Absolute path to the evidence file.
        keyword: Keyword or pattern that matched.
        line_number: 1-based line number for text-like files.
        page_number: 1-based page number for PDF matches.
        paragraph_number: 1-based paragraph number for DOCX matches.
        matched_text: Exact matched substring from the source.
        context: Surrounding context (approx. 20 chars before/after).
        match_position: 0-based character offset within the source unit.
    """

    file_name: str
    absolute_path: str
    keyword: str
    line_number: int | None = None
    page_number: int | None = None
    paragraph_number: int | None = None
    matched_text: str
    context: str
    match_position: int = Field(ge=0)


class KeywordResult(BaseModel):
    """Keyword search outcome for a single evidence file."""

    file_name: str
    absolute_path: str
    file_type: str
    status: SearchStatus
    message: str
    keywords: list[str]
    match_count: int = Field(ge=0)
    matches: list[KeywordMatch] = Field(default_factory=list)
    execution_time_ms: float = Field(ge=0)
    timestamp: datetime


class KeywordSummary(BaseModel):
    """Aggregate statistics across one or more keyword search operations."""

    total_files_searched: int = Field(ge=0)
    files_with_matches: int = Field(ge=0)
    files_without_matches: int = Field(ge=0)
    files_skipped: int = Field(ge=0)
    total_matches: int = Field(ge=0)
    keyword_frequency: dict[str, int] = Field(default_factory=dict)
    execution_time_ms: float = Field(ge=0)
    timestamp: datetime
    status: SearchStatus
    message: str


class SearchResult(BaseModel):
    """Top-level search response containing per-file results and a summary."""

    status: SearchStatus
    message: str
    timestamp: datetime
    results: list[KeywordResult] = Field(default_factory=list)
    summary: KeywordSummary
