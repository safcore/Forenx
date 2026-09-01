"""DOCX document metadata extraction using python-docx."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.exceptions import PackageNotFoundError

from app.hashing.hash_generator import resolve_evidence_path
from app.schemas.metadata import DocumentMetadata, MetadataStatus
from app.utils.config import SUPPORTED_DOCUMENT_EXTENSIONS
from app.utils.exceptions import (
    EvidenceFileError,
    MetadataExtractionError,
    UnsupportedFileTypeError,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _as_optional_str(value: Any) -> str | None:
    """Normalize property values to stripped strings or ``None``."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_optional_datetime(value: Any) -> datetime | None:
    """Normalize datetime-like values to aware UTC datetimes."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None


def _extract_company(document: Document) -> str | None:
    """Extract the Company extended property when present.

    Args:
        document: Opened python-docx document.

    Returns:
        Company name, or ``None`` when unavailable.
    """
    try:
        part = document.part.package.part_related_by(RT.EXTENDED_PROPERTIES)
    except Exception:  # noqa: BLE001 - optional relationship
        return None

    try:
        root = ElementTree.fromstring(part.blob)
    except ElementTree.ParseError:
        return None

    namespace = {"ep": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"}
    node = root.find("ep:Company", namespace)
    if node is None or node.text is None:
        return None
    text = node.text.strip()
    return text or None


def extract_document_metadata(file_path: str | Path) -> DocumentMetadata:
    """Extract forensic metadata from a DOCX evidence file.

    Args:
        file_path: Path to a DOCX document.

    Returns:
        ``DocumentMetadata`` with ``None`` for unavailable properties.

    Raises:
        EvidenceFileError: If the path is invalid or inaccessible.
        UnsupportedFileTypeError: If the extension is not ``.docx``.
        MetadataExtractionError: If the document is invalid/unreadable.
    """
    path = resolve_evidence_path(file_path)
    extension = path.suffix.lower()
    if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Unsupported document type '{extension}'. Expected: .docx"
        )

    logger.info("DOCX metadata extraction started for '%s'", path.name)

    try:
        document = Document(str(path))
    except PermissionError as exc:
        raise EvidenceFileError(
            f"Permission denied while reading document metadata: {path}"
        ) from exc
    except PackageNotFoundError as exc:
        raise MetadataExtractionError(
            f"Invalid or unreadable DOCX document: {path}"
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise MetadataExtractionError(
            f"Failed to extract DOCX metadata from '{path}': {exc}"
        ) from exc

    props = document.core_properties
    result = DocumentMetadata(
        timestamp=datetime.now(timezone.utc),
        status=MetadataStatus.SUCCESS,
        message="Document metadata extracted successfully",
        file_name=path.name,
        title=_as_optional_str(props.title),
        author=_as_optional_str(props.author),
        company=_extract_company(document),
        last_modified_by=_as_optional_str(props.last_modified_by),
        revision=_as_optional_str(props.revision),
        created_date=_as_optional_datetime(props.created),
        modified_date=_as_optional_datetime(props.modified),
        category=_as_optional_str(props.category),
        subject=_as_optional_str(props.subject),
    )
    logger.info("DOCX metadata extraction succeeded for '%s'", path.name)
    return result
