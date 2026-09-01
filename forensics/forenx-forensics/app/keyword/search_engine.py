"""Shared keyword matching utilities for forensic evidence search."""

from __future__ import annotations

import re
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.hashing.hash_generator import resolve_evidence_path
from app.schemas.keyword import KeywordMatch, KeywordResult, SearchStatus
from app.utils.config import KEYWORD_BINARY_PROBE_BYTES, KEYWORD_CONTEXT_CHARS
from app.utils.exceptions import EvidenceFileError, KeywordSearchError
from app.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_CONTEXT_CHARS = KEYWORD_CONTEXT_CHARS
_BINARY_PROBE_BYTES = KEYWORD_BINARY_PROBE_BYTES


@dataclass(frozen=True, slots=True)
class SearchOptions:
    """Configurable keyword search behavior.

    Attributes:
        case_sensitive: When ``True``, matching respects letter case.
        whole_word: When ``True``, require word boundaries around matches.
        regex: When ``True``, treat each keyword as a regular expression.
        context_chars: Number of surrounding characters to include in context.
    """

    case_sensitive: bool = False
    whole_word: bool = False
    regex: bool = False
    context_chars: int = DEFAULT_CONTEXT_CHARS


def normalize_keywords(keywords: str | Sequence[str]) -> list[str]:
    """Normalize caller-provided keywords into a clean list.

    Args:
        keywords: A single keyword or a sequence of keywords.

    Returns:
        Non-empty stripped keyword strings.

    Raises:
        KeywordSearchError: If no usable keywords are provided.
    """
    if isinstance(keywords, str):
        values = [keywords]
    else:
        values = list(keywords)

    normalized = [value.strip() for value in values if value is not None and str(value).strip()]
    if not normalized:
        raise KeywordSearchError("At least one non-empty keyword is required")
    return normalized


def compile_keyword_patterns(
    keywords: Sequence[str],
    options: SearchOptions,
) -> list[tuple[str, re.Pattern[str]]]:
    """Compile keyword patterns according to search options.

    Args:
        keywords: Keywords or regex patterns to search for.
        options: Matching behavior configuration.

    Returns:
        List of ``(original_keyword, compiled_pattern)`` pairs.

    Raises:
        KeywordSearchError: If a regex pattern is invalid.
    """
    flags = 0 if options.case_sensitive else re.IGNORECASE
    compiled: list[tuple[str, re.Pattern[str]]] = []

    for keyword in keywords:
        try:
            expression = keyword if options.regex else re.escape(keyword)
            if options.whole_word:
                expression = rf"\b(?:{expression})\b"
            pattern = re.compile(expression, flags)
        except re.error as exc:
            raise KeywordSearchError(
                f"Invalid regular expression '{keyword}': {exc}"
            ) from exc
        compiled.append((keyword, pattern))

    return compiled


def build_context(
    text: str,
    start: int,
    end: int,
    context_chars: int = DEFAULT_CONTEXT_CHARS,
) -> str:
    """Build a concise surrounding context string for a match.

    Args:
        text: Source text containing the match.
        start: Inclusive match start offset.
        end: Exclusive match end offset.
        context_chars: Characters to include before and after the match.

    Returns:
        Context string with optional leading/trailing ellipses.
    """
    before_start = max(0, start - context_chars)
    after_end = min(len(text), end + context_chars)
    before = text[before_start:start]
    matched = text[start:end]
    after = text[end:after_end]

    prefix = "..." if before_start > 0 else ""
    suffix = "..." if after_end < len(text) else ""
    return f"{prefix}{before}{matched}{after}{suffix}"


def find_matches_in_text(
    text: str,
    patterns: Sequence[tuple[str, re.Pattern[str]]],
    *,
    file_name: str,
    absolute_path: str,
    options: SearchOptions,
    line_number: int | None = None,
    page_number: int | None = None,
    paragraph_number: int | None = None,
) -> list[KeywordMatch]:
    """Find all keyword matches within a text unit.

    Args:
        text: Text to scan (line, page, or paragraph).
        patterns: Compiled keyword patterns.
        file_name: Evidence basename.
        absolute_path: Absolute evidence path.
        options: Search options (used for context size).
        line_number: Optional 1-based line number.
        page_number: Optional 1-based page number.
        paragraph_number: Optional 1-based paragraph number.

    Returns:
        List of structured ``KeywordMatch`` objects.
    """
    matches: list[KeywordMatch] = []
    for keyword, pattern in patterns:
        for match in pattern.finditer(text):
            start, end = match.start(), match.end()
            matches.append(
                KeywordMatch(
                    file_name=file_name,
                    absolute_path=absolute_path,
                    keyword=keyword,
                    line_number=line_number,
                    page_number=page_number,
                    paragraph_number=paragraph_number,
                    matched_text=match.group(0),
                    context=build_context(
                        text,
                        start,
                        end,
                        context_chars=options.context_chars,
                    ),
                    match_position=start,
                )
            )
    return matches


def looks_like_binary(path: Path, probe_size: int = _BINARY_PROBE_BYTES) -> bool:
    """Heuristically determine whether a file appears to be binary.

    Args:
        path: File to inspect.
        probe_size: Number of leading bytes to sample.

    Returns:
        ``True`` when the sample contains NUL bytes or high control-character density.
    """
    try:
        with path.open("rb") as handle:
            sample = handle.read(probe_size)
    except OSError:
        return False

    if not sample:
        return False
    if b"\x00" in sample:
        return True

    # High ratio of non-text control bytes suggests binary content.
    textish = sum(
        1
        for byte in sample
        if byte in (9, 10, 13) or 32 <= byte <= 126 or byte >= 128
    )
    return (textish / len(sample)) < 0.70


def elapsed_ms(started: float) -> float:
    """Return milliseconds elapsed since ``started`` monotonic timestamp."""
    return round((time.perf_counter() - started) * 1000.0, 3)


def make_result(
    *,
    path: Path,
    file_type: str,
    keywords: Sequence[str],
    matches: Iterable[KeywordMatch],
    started: float,
    status: SearchStatus | None = None,
    message: str | None = None,
) -> KeywordResult:
    """Construct a ``KeywordResult`` with derived status and timing."""
    match_list = list(matches)
    if status is None:
        status = (
            SearchStatus.SUCCESS if match_list else SearchStatus.NO_MATCHES
        )
    if message is None:
        if status is SearchStatus.SKIPPED:
            message = "File skipped"
        elif match_list:
            message = f"Found {len(match_list)} match(es)"
        else:
            message = "No matches found"

    return KeywordResult(
        file_name=path.name,
        absolute_path=str(path.resolve()),
        file_type=file_type,
        status=status,
        message=message,
        keywords=list(keywords),
        match_count=len(match_list),
        matches=match_list,
        execution_time_ms=elapsed_ms(started),
        timestamp=datetime.now(timezone.utc),
    )


def ensure_searchable_path(file_path: str | Path) -> Path:
    """Validate an evidence path for keyword search.

    Args:
        file_path: Candidate evidence path.

    Returns:
        Resolved existing file path.

    Raises:
        EvidenceFileError: If the path is empty, missing, or inaccessible.
    """
    try:
        return resolve_evidence_path(file_path)
    except EvidenceFileError:
        raise
    except PermissionError as exc:
        raise EvidenceFileError(
            f"Permission denied while accessing evidence file: {file_path}"
        ) from exc
