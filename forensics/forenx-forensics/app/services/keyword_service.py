"""Keyword search service orchestration for the ForenX forensics engine.

Provides the public Phase 4 API for single-file, multi-keyword, and directory
keyword search across text, PDF, and DOCX evidence, plus hit summaries.

Typical usage example:

    from app.services.keyword_service import KeywordSearchService

    hits = KeywordSearchService().search("evidence/sample_case/sample_notes.txt", "confidential")
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from app.keyword.dispatcher import search_directory as dispatch_search_directory
from app.keyword.dispatcher import search_file
from app.keyword.search_engine import SearchOptions, normalize_keywords
from app.schemas.keyword import (
    KeywordResult,
    KeywordSummary,
    SearchResult,
    SearchStatus,
)
from app.utils.config import KEYWORD_CONTEXT_CHARS
from app.utils.logger import get_logger

logger = get_logger(__name__)


class KeywordSearchService:
    """High-level API for forensic keyword search.

    Designed for reuse by CLI tools, tests, and a future Django backend.
    """

    def __init__(self) -> None:
        """Initialize the keyword search service."""

    def search(
        self,
        file_path: str | Path,
        keyword: str,
        *,
        case_sensitive: bool = False,
        whole_word: bool = False,
        regex: bool = False,
        context_chars: int = KEYWORD_CONTEXT_CHARS,
    ) -> KeywordResult:
        """Search a single evidence file for one keyword.

        Args:
            file_path: Path to the evidence file.
            keyword: Keyword or pattern to find.
            case_sensitive: Enable case-sensitive matching.
            whole_word: Require whole-word boundaries.
            regex: Treat ``keyword`` as a regular expression.
            context_chars: Context window size around each match.

        Returns:
            ``KeywordResult`` for the file.
        """
        return self.search_multiple(
            file_path,
            [keyword],
            case_sensitive=case_sensitive,
            whole_word=whole_word,
            regex=regex,
            context_chars=context_chars,
        )

    def search_multiple(
        self,
        file_path: str | Path,
        keywords: Sequence[str],
        *,
        case_sensitive: bool = False,
        whole_word: bool = False,
        regex: bool = False,
        context_chars: int = KEYWORD_CONTEXT_CHARS,
    ) -> KeywordResult:
        """Search a single evidence file for one or more keywords.

        Args:
            file_path: Path to the evidence file.
            keywords: Keywords or patterns to find.
            case_sensitive: Enable case-sensitive matching.
            whole_word: Require whole-word boundaries.
            regex: Treat keywords as regular expressions.
            context_chars: Context window size around each match.

        Returns:
            ``KeywordResult`` for the file.
        """
        options = SearchOptions(
            case_sensitive=case_sensitive,
            whole_word=whole_word,
            regex=regex,
            context_chars=context_chars,
        )
        logger.info(
            "KeywordSearchService.search_multiple started file=%s keywords=%s",
            Path(file_path).name if file_path else "",
            list(keywords),
        )
        result = search_file(file_path, keywords, options=options)
        logger.info(
            "KeywordSearchService.search_multiple finished file=%s matches=%d "
            "status=%s time_ms=%.3f",
            result.file_name,
            result.match_count,
            result.status.value,
            result.execution_time_ms,
        )
        return result

    def search_directory(
        self,
        directory: str | Path,
        keywords: str | Sequence[str],
        *,
        case_sensitive: bool = False,
        whole_word: bool = False,
        regex: bool = False,
        context_chars: int = KEYWORD_CONTEXT_CHARS,
        recursive: bool = False,
    ) -> SearchResult:
        """Search a directory of evidence files and summarize outcomes.

        Args:
            directory: Directory containing evidence files.
            keywords: Keyword, pattern, or list of keywords/patterns.
            case_sensitive: Enable case-sensitive matching.
            whole_word: Require whole-word boundaries.
            regex: Treat keywords as regular expressions.
            context_chars: Context window size around each match.
            recursive: Walk subdirectories when ``True``.

        Returns:
            ``SearchResult`` containing per-file results and a summary.
        """
        options = SearchOptions(
            case_sensitive=case_sensitive,
            whole_word=whole_word,
            regex=regex,
            context_chars=context_chars,
        )
        keyword_list = normalize_keywords(keywords)
        logger.info(
            "KeywordSearchService.search_directory started dir=%s keywords=%s",
            directory,
            keyword_list,
        )

        results = dispatch_search_directory(
            directory,
            keyword_list,
            options=options,
            recursive=recursive,
        )
        summary = self.summarize_results(results)
        status = (
            SearchStatus.SUCCESS
            if summary.total_matches > 0
            else SearchStatus.NO_MATCHES
        )
        message = (
            f"Directory search complete: {summary.total_matches} match(es) "
            f"across {summary.files_with_matches} file(s)"
        )
        response = SearchResult(
            status=status,
            message=message,
            timestamp=datetime.now(timezone.utc),
            results=results,
            summary=summary,
        )
        logger.info(
            "KeywordSearchService.search_directory finished files=%d matches=%d "
            "time_ms=%.3f",
            summary.total_files_searched,
            summary.total_matches,
            summary.execution_time_ms,
        )
        return response

    def summarize_results(self, results: Sequence[KeywordResult]) -> KeywordSummary:
        """Build aggregate statistics for a collection of file results.

        Args:
            results: Per-file keyword search outcomes.

        Returns:
            ``KeywordSummary`` with counts, frequencies, and timing.
        """
        files_with_matches = sum(1 for item in results if item.match_count > 0)
        files_skipped = sum(
            1 for item in results if item.status is SearchStatus.SKIPPED
        )
        files_without_matches = sum(
            1
            for item in results
            if item.status is not SearchStatus.SKIPPED and item.match_count == 0
        )
        total_matches = sum(item.match_count for item in results)
        frequency: Counter[str] = Counter()
        for item in results:
            for match in item.matches:
                frequency[match.keyword] += 1

        execution_time_ms = round(sum(item.execution_time_ms for item in results), 3)
        status = (
            SearchStatus.SUCCESS if total_matches > 0 else SearchStatus.NO_MATCHES
        )
        message = (
            f"Summarized {len(results)} file result(s) with {total_matches} match(es)"
        )

        return KeywordSummary(
            total_files_searched=len(results),
            files_with_matches=files_with_matches,
            files_without_matches=files_without_matches,
            files_skipped=files_skipped,
            total_matches=total_matches,
            keyword_frequency=dict(frequency),
            execution_time_ms=execution_time_ms,
            timestamp=datetime.now(timezone.utc),
            status=status,
            message=message,
        )
