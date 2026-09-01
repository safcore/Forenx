"""Metadata extraction service orchestration for the ForenX engine.

Provides the public Phase 3 API for image, PDF, DOCX, and filesystem metadata
extraction. Missing optional fields are represented as ``None``.

Typical usage example:

    from app.services.metadata_service import MetadataService

    result = MetadataService().extract("evidence/sample_case/sample_image.png")
"""

from __future__ import annotations

from pathlib import Path

from app.metadata.extractor import (
    extract_document,
    extract_filesystem,
    extract_image,
    extract_metadata,
    extract_pdf,
)
from app.schemas.metadata import (
    DocumentMetadata,
    FileMetadata,
    ImageMetadata,
    MetadataResult,
    PdfMetadata,
)
from app.services.hash_service import HashService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MetadataService:
    """High-level API for forensic metadata extraction.

    Designed for reuse by CLI tools, tests, and a future Django backend.
    """

    def __init__(self, hash_service: HashService | None = None) -> None:
        """Initialize the service.

        Args:
            hash_service: Optional shared Phase 2 ``HashService`` used when
                collecting filesystem SHA256 digests.
        """
        self._hash_service = hash_service or HashService()

    def extract(self, file_path: str | Path) -> MetadataResult:
        """Detect evidence type and extract all applicable metadata.

        Args:
            file_path: Path to the evidence file.

        Returns:
            Aggregated ``MetadataResult``.
        """
        logger.info(
            "MetadataService.extract started for '%s'",
            Path(file_path).name if file_path else "",
        )
        result = extract_metadata(file_path, hash_service=self._hash_service)
        logger.info(
            "MetadataService.extract finished file_type=%s status=%s",
            result.file_type,
            result.status.value,
        )
        return result

    def extract_image(self, file_path: str | Path) -> ImageMetadata:
        """Extract metadata from an image evidence file.

        Args:
            file_path: Path to a supported image.

        Returns:
            ``ImageMetadata`` model.
        """
        logger.info(
            "MetadataService.extract_image started for '%s'",
            Path(file_path).name if file_path else "",
        )
        result = extract_image(file_path)
        logger.info(
            "MetadataService.extract_image finished status=%s",
            result.status.value,
        )
        return result

    def extract_pdf(self, file_path: str | Path) -> PdfMetadata:
        """Extract metadata from a PDF evidence file.

        Args:
            file_path: Path to a PDF document.

        Returns:
            ``PdfMetadata`` model.
        """
        logger.info(
            "MetadataService.extract_pdf started for '%s'",
            Path(file_path).name if file_path else "",
        )
        result = extract_pdf(file_path)
        logger.info(
            "MetadataService.extract_pdf finished status=%s encrypted=%s",
            result.status.value,
            result.encrypted,
        )
        return result

    def extract_document(self, file_path: str | Path) -> DocumentMetadata:
        """Extract metadata from a DOCX evidence file.

        Args:
            file_path: Path to a DOCX document.

        Returns:
            ``DocumentMetadata`` model.
        """
        logger.info(
            "MetadataService.extract_document started for '%s'",
            Path(file_path).name if file_path else "",
        )
        result = extract_document(file_path)
        logger.info(
            "MetadataService.extract_document finished status=%s",
            result.status.value,
        )
        return result

    def extract_filesystem(self, file_path: str | Path) -> FileMetadata:
        """Extract filesystem metadata for any evidence file.

        Args:
            file_path: Path to an evidence file.

        Returns:
            ``FileMetadata`` model including SHA256 from Phase 2 hashing.
        """
        logger.info(
            "MetadataService.extract_filesystem started for '%s'",
            Path(file_path).name if file_path else "",
        )
        result = extract_filesystem(file_path, hash_service=self._hash_service)
        logger.info(
            "MetadataService.extract_filesystem finished status=%s",
            result.status.value,
        )
        return result
