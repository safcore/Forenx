"""Keyword search dispatcher for supported evidence file types."""

from __future__ import annotations

import time
from collections.abc import Sequence
from enum import Enum
from pathlib import Path

from app.keyword.document_search import (
    SUPPORTED_DOCUMENT_EXTENSIONS,
    search_document_file,
)
from app.keyword.pdf_search import SUPPORTED_PDF_EXTENSIONS, search_pdf_file
from app.keyword.search_engine import (
    SearchOptions,
    ensure_searchable_path,
    looks_like_binary,
    make_result,
    normalize_keywords,
)
from app.keyword.text_search import SUPPORTED_TEXT_EXTENSIONS, search_text_file
from app.schemas.keyword import KeywordResult, SearchStatus
from app.utils.exceptions import UnsupportedFileTypeError
from app.utils.logger import get_logger

logger = get_logger(__name__)

SUPPORTED_KEYWORD_EXTENSIONS: frozenset[str] = (
    SUPPORTED_TEXT_EXTENSIONS
    | SUPPORTED_PDF_EXTENSIONS
    | SUPPORTED_DOCUMENT_EXTENSIONS
)


class KeywordFileType(str, Enum):
    """Supported Phase 4 keyword-search evidence categories."""

    TEXT = "text"
    PDF = "pdf"
    DOCX = "docx"


def detect_keyword_file_type(file_path: str | Path) -> KeywordFileType:
    """Detect which keyword searcher should handle a file.

    Args:
        file_path: Path to an evidence file.

    Returns:
        Detected ``KeywordFileType``.

    Raises:
        EvidenceFileError: If the path is invalid.
        UnsupportedFileTypeError: If the extension is unsupported.
    """
    path = ensure_searchable_path(file_path)
    extension = path.suffix.lower()

    if extension in SUPPORTED_TEXT_EXTENSIONS:
        return KeywordFileType.TEXT
    if extension in SUPPORTED_PDF_EXTENSIONS:
        return KeywordFileType.PDF
    if extension in SUPPORTED_DOCUMENT_EXTENSIONS:
        return KeywordFileType.DOCX

    supported = ", ".join(sorted(SUPPORTED_KEYWORD_EXTENSIONS))
    raise UnsupportedFileTypeError(
        f"Unsupported evidence type for keyword search: '{extension}'. "
        f"Supported: {supported}"
    )


def search_file(
    file_path: str | Path,
    keywords: str | Sequence[str],
    *,
    options: SearchOptions | None = None,
    skip_unsupported: bool = False,
    skip_binary: bool = True,
) -> KeywordResult:
    """Dispatch keyword search to the appropriate extractor.

    Args:
        file_path: Path to the evidence file.
        keywords: Keyword or list of keywords/patterns.
        options: Optional search behavior configuration.
        skip_unsupported: When ``True``, unsupported files return SKIPPED
            instead of raising.
        skip_binary: When ``True``, binary-looking files are skipped.

    Returns:
        ``KeywordResult`` for the file.

    Raises:
        EvidenceFileError: If the path is invalid or inaccessible.
        UnsupportedFileTypeError: If unsupported and not skipped.
        KeywordSearchError: If keywords/regex are invalid or parsing fails.
    """
    options = options or SearchOptions()
    path = ensure_searchable_path(file_path)
    keyword_list = normalize_keywords(keywords)
    started = time.perf_counter()

    logger.info(
        "Keyword search dispatch started for '%s' keywords=%s",
        path.name,
        keyword_list,
    )

    extension = path.suffix.lower()
    if extension not in SUPPORTED_KEYWORD_EXTENSIONS:
        if skip_unsupported:
            logger.warning(
                "Skipping unsupported file '%s' extension=%s",
                path.name,
                extension,
            )
            return make_result(
                path=path,
                file_type=extension.lstrip(".") or "unknown",
                keywords=keyword_list,
                matches=[],
                started=started,
                status=SearchStatus.SKIPPED,
                message=f"Skipped unsupported file type '{extension}'",
            )
        detect_keyword_file_type(path)  # raises UnsupportedFileTypeError

    if skip_binary and extension in SUPPORTED_TEXT_EXTENSIONS and looks_like_binary(path):
        logger.warning("Skipping binary file '%s'", path.name)
        return make_result(
            path=path,
            file_type=extension.lstrip(".") or "text",
            keywords=keyword_list,
            matches=[],
            started=started,
            status=SearchStatus.SKIPPED,
            message="Skipped binary file",
        )

    file_type = detect_keyword_file_type(path)
    logger.info(
        "Detected keyword file type '%s' for '%s'",
        file_type.value,
        path.name,
    )

    if file_type is KeywordFileType.TEXT:
        return search_text_file(path, keyword_list, options=options)
    if file_type is KeywordFileType.PDF:
        return search_pdf_file(path, keyword_list, options=options)
    return search_document_file(path, keyword_list, options=options)


def search_directory(
    directory: str | Path,
    keywords: str | Sequence[str],
    *,
    options: SearchOptions | None = None,
    recursive: bool = False,
) -> list[KeywordResult]:
    """Search all supported files inside a directory.

    Unsupported and binary files are skipped gracefully.

    Args:
        directory: Directory containing evidence files.
        keywords: Keyword or list of keywords/patterns.
        options: Optional search behavior configuration.
        recursive: When ``True``, walk subdirectories.

    Returns:
        List of per-file ``KeywordResult`` objects.

    Raises:
        EvidenceFileError: If the directory path is invalid.
        KeywordSearchError: If keywords/regex are invalid.
    """
    from app.utils.exceptions import EvidenceFileError

    options = options or SearchOptions()
    keyword_list = normalize_keywords(keywords)
    root = Path(directory)

    if not str(directory).strip():
        raise EvidenceFileError("Evidence directory path must not be empty")
    if not root.exists():
        raise EvidenceFileError(f"Evidence directory not found: {root}")
    if not root.is_dir():
        raise EvidenceFileError(f"Evidence path is not a directory: {root}")

    logger.info(
        "Directory keyword search started for '%s' recursive=%s keywords=%s",
        root,
        recursive,
        keyword_list,
    )

    iterator = root.rglob("*") if recursive else root.iterdir()
    results: list[KeywordResult] = []

    for candidate in sorted(iterator, key=lambda item: str(item).lower()):
        if not candidate.is_file():
            continue
        results.append(
            search_file(
                candidate,
                keyword_list,
                options=options,
                skip_unsupported=True,
                skip_binary=True,
            )
        )

    logger.info(
        "Directory keyword search finished for '%s' files=%d",
        root,
        len(results),
    )
    return results
