"""Keyword search for PDF evidence files."""

from __future__ import annotations

import time
from collections.abc import Sequence
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.keyword.search_engine import (
    SearchOptions,
    compile_keyword_patterns,
    ensure_searchable_path,
    find_matches_in_text,
    make_result,
    normalize_keywords,
)
from app.schemas.keyword import KeywordResult
from app.utils.config import SUPPORTED_PDF_EXTENSIONS
from app.utils.exceptions import (
    EvidenceFileError,
    KeywordSearchError,
    UnsupportedFileTypeError,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def search_pdf_file(
    file_path: str | Path,
    keywords: str | Sequence[str],
    *,
    options: SearchOptions | None = None,
) -> KeywordResult:
    """Search a PDF evidence file page by page.

    Args:
        file_path: Path to a PDF document.
        keywords: Keyword or list of keywords/patterns.
        options: Optional search behavior configuration.

    Returns:
        ``KeywordResult`` with page-scoped matches.

    Raises:
        EvidenceFileError: If the path is invalid or inaccessible.
        UnsupportedFileTypeError: If the extension is not ``.pdf``.
        KeywordSearchError: If the PDF cannot be parsed/searched.
    """
    options = options or SearchOptions()
    path = ensure_searchable_path(file_path)
    if path.suffix.lower() not in SUPPORTED_PDF_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Unsupported PDF type '{path.suffix.lower()}'. Expected: .pdf"
        )

    keyword_list = normalize_keywords(keywords)
    started = time.perf_counter()
    logger.info(
        "PDF keyword search started for '%s' keywords=%s",
        path.name,
        keyword_list,
    )

    try:
        reader = PdfReader(str(path))
    except PermissionError as exc:
        raise EvidenceFileError(
            f"Permission denied while reading PDF: {path}"
        ) from exc
    except PdfReadError as exc:
        raise KeywordSearchError(f"Invalid or unreadable PDF: {path}") from exc
    except OSError as exc:
        raise KeywordSearchError(f"Failed to open PDF '{path}': {exc}") from exc

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:  # noqa: BLE001
            logger.warning(
                "Encrypted PDF '%s' could not be decrypted; searching available text",
                path.name,
            )

    patterns = compile_keyword_patterns(keyword_list, options)
    matches = []
    absolute = str(path.resolve())

    try:
        for page_index, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to extract text from PDF '%s' page %d: %s",
                    path.name,
                    page_index,
                    exc,
                )
                continue

            matches.extend(
                find_matches_in_text(
                    text,
                    patterns,
                    file_name=path.name,
                    absolute_path=absolute,
                    options=options,
                    page_number=page_index,
                )
            )
    except Exception as exc:  # noqa: BLE001
        raise KeywordSearchError(
            f"Failed while searching PDF '{path}': {exc}"
        ) from exc

    result = make_result(
        path=path,
        file_type="pdf",
        keywords=keyword_list,
        matches=matches,
        started=started,
    )
    logger.info(
        "PDF keyword search finished for '%s' matches=%d time_ms=%.3f",
        path.name,
        result.match_count,
        result.execution_time_ms,
    )
    return result
