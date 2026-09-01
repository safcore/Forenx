"""Metadata extraction dispatcher for supported evidence file types."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from app.hashing.hash_generator import resolve_evidence_path
from app.metadata.document_metadata import (
    SUPPORTED_DOCUMENT_EXTENSIONS,
    extract_document_metadata,
)
from app.metadata.filesystem_metadata import extract_filesystem_metadata
from app.metadata.image_metadata import (
    SUPPORTED_IMAGE_EXTENSIONS,
    extract_image_metadata,
)
from app.metadata.pdf_metadata import SUPPORTED_PDF_EXTENSIONS, extract_pdf_metadata
from app.schemas.metadata import (
    DocumentMetadata,
    FileMetadata,
    ImageMetadata,
    MetadataResult,
    MetadataStatus,
    PdfMetadata,
)
from app.utils.exceptions import UnsupportedFileTypeError
from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.services.hash_service import HashService

logger = get_logger(__name__)


class EvidenceFileType(str, Enum):
    """Supported Phase 3 metadata evidence categories."""

    IMAGE = "image"
    PDF = "pdf"
    DOCX = "docx"
    FILESYSTEM = "filesystem"


def detect_file_type(file_path: str | Path) -> EvidenceFileType:
    """Detect the metadata extractor category for a file.

    Args:
        file_path: Path to an evidence file.

    Returns:
        Detected ``EvidenceFileType``.

    Raises:
        EvidenceFileError: If the path is invalid.
        UnsupportedFileTypeError: If no specialized extractor applies.
    """
    path = resolve_evidence_path(file_path)
    extension = path.suffix.lower()

    if extension in SUPPORTED_IMAGE_EXTENSIONS:
        return EvidenceFileType.IMAGE
    if extension in SUPPORTED_PDF_EXTENSIONS:
        return EvidenceFileType.PDF
    if extension in SUPPORTED_DOCUMENT_EXTENSIONS:
        return EvidenceFileType.DOCX

    raise UnsupportedFileTypeError(
        f"Unsupported evidence type for metadata extraction: '{extension}'"
    )


def extract_metadata(
    file_path: str | Path,
    *,
    hash_service: HashService | None = None,
) -> MetadataResult:
    """Detect file type and extract filesystem plus type-specific metadata.

    Args:
        file_path: Path to the evidence file.
        hash_service: Optional shared ``HashService`` for filesystem SHA256.

    Returns:
        Aggregated ``MetadataResult``.

    Raises:
        EvidenceFileError: If the path is invalid or inaccessible.
        UnsupportedFileTypeError: If the extension is unsupported.
        MetadataExtractionError: If specialized extraction fails.
    """
    path = resolve_evidence_path(file_path)
    logger.info("Metadata extraction started for '%s'", path.name)

    file_type = detect_file_type(path)
    logger.info(
        "Detected file type '%s' for '%s'; selecting extractor",
        file_type.value,
        path.name,
    )

    filesystem = extract_filesystem_metadata(path, hash_service=hash_service)
    image: ImageMetadata | None = None
    pdf: PdfMetadata | None = None
    document: DocumentMetadata | None = None

    if file_type is EvidenceFileType.IMAGE:
        image = extract_image_metadata(path)
    elif file_type is EvidenceFileType.PDF:
        pdf = extract_pdf_metadata(path)
    elif file_type is EvidenceFileType.DOCX:
        document = extract_document_metadata(path)

    specialized_status = None
    if image is not None:
        specialized_status = image.status
    elif pdf is not None:
        specialized_status = pdf.status
    elif document is not None:
        specialized_status = document.status

    if (
        filesystem.status == MetadataStatus.PARTIAL
        or specialized_status == MetadataStatus.PARTIAL
    ):
        status = MetadataStatus.PARTIAL
        message = "Metadata extracted with one or more unavailable fields"
    else:
        status = MetadataStatus.SUCCESS
        message = "Metadata extracted successfully"

    result = MetadataResult(
        timestamp=filesystem.timestamp,
        status=status,
        message=message,
        file_type=file_type.value,
        file_name=path.name,
        filesystem=filesystem,
        image=image,
        pdf=pdf,
        document=document,
    )
    logger.info(
        "Metadata extraction succeeded for '%s' file_type=%s status=%s",
        path.name,
        file_type.value,
        status.value,
    )
    return result


def extract_image(file_path: str | Path) -> ImageMetadata:
    """Extract image metadata for an evidence file."""
    return extract_image_metadata(file_path)


def extract_pdf(file_path: str | Path) -> PdfMetadata:
    """Extract PDF metadata for an evidence file."""
    return extract_pdf_metadata(file_path)


def extract_document(file_path: str | Path) -> DocumentMetadata:
    """Extract DOCX metadata for an evidence file."""
    return extract_document_metadata(file_path)


def extract_filesystem(
    file_path: str | Path,
    *,
    hash_service: HashService | None = None,
) -> FileMetadata:
    """Extract filesystem metadata for an evidence file."""
    return extract_filesystem_metadata(file_path, hash_service=hash_service)
