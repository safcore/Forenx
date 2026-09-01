"""PDF metadata extraction using pypdf."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.hashing.hash_generator import resolve_evidence_path
from app.schemas.metadata import MetadataStatus, PdfMetadata
from app.utils.config import SUPPORTED_PDF_EXTENSIONS
from app.utils.exceptions import (
    EvidenceFileError,
    MetadataExtractionError,
    UnsupportedFileTypeError,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _parse_pdf_date(value: Any) -> datetime | None:
    """Parse PDF date strings such as ``D:20240101120000+00'00'``.

    Args:
        value: Raw PDF date value.

    Returns:
        Aware UTC datetime when parsing succeeds; otherwise ``None``.
    """
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    if text.startswith("D:"):
        text = text[2:]

    # Keep the compact YYYYMMDDHHMMSS prefix when present.
    compact = "".join(ch for ch in text if ch.isdigit())
    for length, fmt in ((14, "%Y%m%d%H%M%S"), (12, "%Y%m%d%H%M"), (8, "%Y%m%d")):
        if len(compact) >= length:
            try:
                parsed = datetime.strptime(compact[:length], fmt)
                return parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def _meta_get(metadata: Any, *names: str) -> str | None:
    """Read the first present text field from PDF metadata.

    Args:
        metadata: pypdf metadata object.
        *names: Candidate attribute / key names.

    Returns:
        Stripped string value, or ``None`` when absent.
    """
    if metadata is None:
        return None

    for name in names:
        value = None
        if hasattr(metadata, name):
            value = getattr(metadata, name)
        elif hasattr(metadata, "get"):
            value = metadata.get(name)

        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def extract_pdf_metadata(file_path: str | Path) -> PdfMetadata:
    """Extract forensic metadata from a PDF evidence file.

    Args:
        file_path: Path to a PDF document.

    Returns:
        ``PdfMetadata`` with ``None`` for unavailable document-info fields.

    Raises:
        EvidenceFileError: If the path is invalid or inaccessible.
        UnsupportedFileTypeError: If the extension is not ``.pdf``.
        MetadataExtractionError: If the PDF is invalid/unreadable.
    """
    path = resolve_evidence_path(file_path)
    extension = path.suffix.lower()
    if extension not in SUPPORTED_PDF_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Unsupported PDF type '{extension}'. Expected: .pdf"
        )

    logger.info("PDF metadata extraction started for '%s'", path.name)

    try:
        reader = PdfReader(str(path))
    except PermissionError as exc:
        raise EvidenceFileError(
            f"Permission denied while reading PDF metadata: {path}"
        ) from exc
    except PdfReadError as exc:
        raise MetadataExtractionError(
            f"Invalid or unreadable PDF document: {path}"
        ) from exc
    except OSError as exc:
        raise MetadataExtractionError(
            f"Failed to open PDF '{path}': {exc}"
        ) from exc

    encrypted = bool(reader.is_encrypted)
    page_count: int | None = None
    info = None

    if encrypted:
        # Encrypted PDFs may still expose encryption state without a password.
        logger.warning(
            "PDF '%s' is encrypted; limited metadata may be available",
            path.name,
        )
        try:
            # Empty password attempt; ignore failure and keep partial data.
            reader.decrypt("")
        except Exception:  # noqa: BLE001
            pass

    try:
        page_count = len(reader.pages)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Unable to read page count for '%s': %s", path.name, exc)
        page_count = None

    try:
        info = reader.metadata
    except Exception as exc:  # noqa: BLE001
        logger.warning("Unable to read PDF info for '%s': %s", path.name, exc)
        info = None

    status = (
        MetadataStatus.PARTIAL
        if encrypted and (info is None or page_count is None)
        else MetadataStatus.SUCCESS
    )
    message = (
        "PDF metadata extracted with limitations due to encryption"
        if status == MetadataStatus.PARTIAL
        else "PDF metadata extracted successfully"
    )

    creation_raw = None
    modification_raw = None
    if info is not None:
        creation_raw = getattr(info, "creation_date", None) or _meta_get(
            info, "creation_date", "/CreationDate"
        )
        modification_raw = getattr(info, "modification_date", None) or _meta_get(
            info, "modification_date", "/ModDate"
        )

    result = PdfMetadata(
        timestamp=datetime.now(timezone.utc),
        status=status,
        message=message,
        file_name=path.name,
        title=_meta_get(info, "title", "/Title"),
        author=_meta_get(info, "author", "/Author"),
        creator=_meta_get(info, "creator", "/Creator"),
        producer=_meta_get(info, "producer", "/Producer"),
        subject=_meta_get(info, "subject", "/Subject"),
        keywords=_meta_get(info, "keywords", "/Keywords"),
        creation_date=_parse_pdf_date(creation_raw),
        modification_date=_parse_pdf_date(modification_raw),
        page_count=page_count,
        encrypted=encrypted,
    )
    logger.info(
        "PDF metadata extraction succeeded for '%s' encrypted=%s pages=%s",
        path.name,
        encrypted,
        page_count,
    )
    return result
