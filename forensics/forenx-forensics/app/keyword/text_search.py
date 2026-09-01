"""Streaming keyword search for text-like evidence files."""

from __future__ import annotations

import time
from collections.abc import Sequence
from pathlib import Path

from app.keyword.search_engine import (
    SearchOptions,
    compile_keyword_patterns,
    ensure_searchable_path,
    find_matches_in_text,
    looks_like_binary,
    make_result,
    normalize_keywords,
)
from app.schemas.keyword import KeywordResult, SearchStatus
from app.utils.config import SUPPORTED_TEXT_EXTENSIONS
from app.utils.exceptions import (
    EvidenceFileError,
    KeywordSearchError,
    UnsupportedFileTypeError,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def search_text_file(
    file_path: str | Path,
    keywords: str | Sequence[str],
    *,
    options: SearchOptions | None = None,
) -> KeywordResult:
    """Search a text-like evidence file line-by-line.

    Args:
        file_path: Path to a TXT/LOG/CSV/JSON/XML file.
        keywords: Keyword or list of keywords/patterns.
        options: Optional search behavior configuration.

    Returns:
        ``KeywordResult`` describing matches in the file.

    Raises:
        EvidenceFileError: If the path is invalid or unreadable.
        UnsupportedFileTypeError: If the extension is not text-like.
        KeywordSearchError: If keywords/regex are invalid.
    """
    options = options or SearchOptions()
    path = ensure_searchable_path(file_path)
    extension = path.suffix.lower()
    if extension not in SUPPORTED_TEXT_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_TEXT_EXTENSIONS))
        raise UnsupportedFileTypeError(
            f"Unsupported text type '{extension}'. Supported: {supported}"
        )

    keyword_list = normalize_keywords(keywords)
    started = time.perf_counter()
    logger.info(
        "Text keyword search started for '%s' keywords=%s",
        path.name,
        keyword_list,
    )

    if looks_like_binary(path):
        logger.warning("Skipping binary-looking text file '%s'", path.name)
        return make_result(
            path=path,
            file_type=extension.lstrip(".") or "text",
            keywords=keyword_list,
            matches=[],
            started=started,
            status=SearchStatus.SKIPPED,
            message="Skipped binary file",
        )

    patterns = compile_keyword_patterns(keyword_list, options)
    matches = []
    absolute = str(path.resolve())

    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            for line_number, line in enumerate(handle, start=1):
                # Preserve searchable content but strip only the trailing newline.
                content = line.rstrip("\r\n")
                matches.extend(
                    find_matches_in_text(
                        content,
                        patterns,
                        file_name=path.name,
                        absolute_path=absolute,
                        options=options,
                        line_number=line_number,
                    )
                )
    except PermissionError as exc:
        raise EvidenceFileError(
            f"Permission denied while reading evidence file: {path}"
        ) from exc
    except OSError as exc:
        raise KeywordSearchError(f"Failed to search text file '{path}': {exc}") from exc

    result = make_result(
        path=path,
        file_type=extension.lstrip(".") or "text",
        keywords=keyword_list,
        matches=matches,
        started=started,
    )
    logger.info(
        "Text keyword search finished for '%s' matches=%d time_ms=%.3f",
        path.name,
        result.match_count,
        result.execution_time_ms,
    )
    return result
