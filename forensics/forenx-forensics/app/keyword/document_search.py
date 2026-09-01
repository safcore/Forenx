"""Keyword search for DOCX evidence files."""

from __future__ import annotations

import time
from collections.abc import Sequence
from pathlib import Path

from docx import Document
from docx.opc.exceptions import PackageNotFoundError

from app.keyword.search_engine import (
    SearchOptions,
    compile_keyword_patterns,
    ensure_searchable_path,
    find_matches_in_text,
    make_result,
    normalize_keywords,
)
from app.schemas.keyword import KeywordResult
from app.utils.config import SUPPORTED_DOCUMENT_EXTENSIONS
from app.utils.exceptions import (
    EvidenceFileError,
    KeywordSearchError,
    UnsupportedFileTypeError,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def search_document_file(
    file_path: str | Path,
    keywords: str | Sequence[str],
    *,
    options: SearchOptions | None = None,
) -> KeywordResult:
    """Search a DOCX evidence file paragraph by paragraph.

    Args:
        file_path: Path to a DOCX document.
        keywords: Keyword or list of keywords/patterns.
        options: Optional search behavior configuration.

    Returns:
        ``KeywordResult`` with paragraph-scoped matches.

    Raises:
        EvidenceFileError: If the path is invalid or inaccessible.
        UnsupportedFileTypeError: If the extension is not ``.docx``.
        KeywordSearchError: If the document cannot be parsed/searched.
    """
    options = options or SearchOptions()
    path = ensure_searchable_path(file_path)
    if path.suffix.lower() not in SUPPORTED_DOCUMENT_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Unsupported document type '{path.suffix.lower()}'. Expected: .docx"
        )

    keyword_list = normalize_keywords(keywords)
    started = time.perf_counter()
    logger.info(
        "DOCX keyword search started for '%s' keywords=%s",
        path.name,
        keyword_list,
    )

    try:
        document = Document(str(path))
    except PermissionError as exc:
        raise EvidenceFileError(
            f"Permission denied while reading DOCX: {path}"
        ) from exc
    except PackageNotFoundError as exc:
        raise KeywordSearchError(f"Invalid or unreadable DOCX: {path}") from exc
    except Exception as exc:  # noqa: BLE001
        raise KeywordSearchError(
            f"Failed to open DOCX '{path}': {exc}"
        ) from exc

    patterns = compile_keyword_patterns(keyword_list, options)
    matches = []
    absolute = str(path.resolve())

    for paragraph_number, paragraph in enumerate(document.paragraphs, start=1):
        text = paragraph.text or ""
        if not text:
            continue
        matches.extend(
            find_matches_in_text(
                text,
                patterns,
                file_name=path.name,
                absolute_path=absolute,
                options=options,
                paragraph_number=paragraph_number,
            )
        )

    result = make_result(
        path=path,
        file_type="docx",
        keywords=keyword_list,
        matches=matches,
        started=started,
    )
    logger.info(
        "DOCX keyword search finished for '%s' matches=%d time_ms=%.3f",
        path.name,
        result.match_count,
        result.execution_time_ms,
    )
    return result
