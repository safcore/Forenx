"""Pydantic schemas for forensic metadata extraction results."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class MetadataStatus(str, Enum):
    """Outcome status for a metadata extraction operation."""

    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"


class BaseMetadata(BaseModel):
    """Shared fields for all metadata result models.

    Attributes:
        timestamp: UTC time when extraction completed.
        status: High-level extraction outcome.
        message: Human-readable status description.
    """

    timestamp: datetime
    status: MetadataStatus
    message: str


class FileMetadata(BaseMetadata):
    """Filesystem metadata for an evidence file.

    Attributes:
        file_name: Basename of the file.
        absolute_path: Absolute filesystem path.
        extension: File extension including the leading dot.
        mime_type: Detected MIME type, if available.
        file_size: Size in bytes.
        created_time: Filesystem creation / birth time when available.
        modified_time: Last content modification time.
        accessed_time: Last access time.
        readable: Whether the current process can read the file.
        writable: Whether the current process can write the file.
        hidden: Whether the file appears hidden on the host OS.
        sha256: SHA256 digest computed via Phase 2 hashing.
    """

    file_name: str
    absolute_path: str
    extension: str
    mime_type: str | None = None
    file_size: int = Field(ge=0)
    created_time: datetime | None = None
    modified_time: datetime | None = None
    accessed_time: datetime | None = None
    readable: bool
    writable: bool
    hidden: bool
    sha256: str | None = None


class ImageMetadata(BaseMetadata):
    """Metadata extracted from an image evidence file.

    Missing EXIF fields are represented as ``None``.
    """

    filename: str
    extension: str
    mime_type: str | None = None
    file_size: int = Field(ge=0)
    width: int | None = None
    height: int | None = None
    camera_make: str | None = None
    camera_model: str | None = None
    software: str | None = None
    date_taken: datetime | None = None
    gps_latitude: float | None = None
    gps_longitude: float | None = None
    orientation: int | None = None
    color_mode: str | None = None


class PdfMetadata(BaseMetadata):
    """Metadata extracted from a PDF evidence file.

    Missing document-info fields are represented as ``None``.
    """

    file_name: str
    title: str | None = None
    author: str | None = None
    creator: str | None = None
    producer: str | None = None
    subject: str | None = None
    keywords: str | None = None
    creation_date: datetime | None = None
    modification_date: datetime | None = None
    page_count: int | None = None
    encrypted: bool


class DocumentMetadata(BaseMetadata):
    """Metadata extracted from a DOCX evidence file.

    Missing core-property fields are represented as ``None``.
    """

    file_name: str
    title: str | None = None
    author: str | None = None
    company: str | None = None
    last_modified_by: str | None = None
    revision: str | None = None
    created_date: datetime | None = None
    modified_date: datetime | None = None
    category: str | None = None
    subject: str | None = None


class MetadataResult(BaseMetadata):
    """Aggregated metadata extraction result for an evidence file.

    Attributes:
        file_type: Detected evidence category used for dispatch.
        file_name: Basename of the analyzed file.
        filesystem: Always populated when extraction succeeds.
        image: Populated for image evidence.
        pdf: Populated for PDF evidence.
        document: Populated for DOCX evidence.
    """

    file_type: Literal["image", "pdf", "docx", "filesystem"]
    file_name: str
    filesystem: FileMetadata | None = None
    image: ImageMetadata | None = None
    pdf: PdfMetadata | None = None
    document: DocumentMetadata | None = None
