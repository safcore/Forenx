"""Comprehensive tests for Phase 3 metadata extraction."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from docx import Document
from PIL import ExifTags, Image
from pypdf import PdfWriter

from app.hashing.hash_generator import generate_sha256
from app.metadata.extractor import detect_file_type, extract_metadata
from app.schemas.metadata import MetadataStatus
from app.services.metadata_service import MetadataService
from app.utils.exceptions import (
    EvidenceFileError,
    MetadataExtractionError,
    UnsupportedFileTypeError,
)


@pytest.fixture
def jpeg_with_exif(tmp_path: Path) -> Path:
    """Create a small JPEG containing basic EXIF tags."""
    path = tmp_path / "camera.jpg"
    image = Image.new("RGB", (32, 24), color=(12, 34, 56))
    exif = image.getexif()
    exif[ExifTags.Base.Make] = "ForenXCam"
    exif[ExifTags.Base.Model] = "FX-100"
    exif[ExifTags.Base.Software] = "ForenX Test Suite"
    exif[ExifTags.Base.DateTime] = "2024:01:02 03:04:05"
    exif[ExifTags.Base.Orientation] = 1
    image.save(path, format="JPEG", exif=exif)
    return path


@pytest.fixture
def png_without_exif(tmp_path: Path) -> Path:
    """Create a PNG without EXIF metadata."""
    path = tmp_path / "plain.png"
    Image.new("RGB", (16, 10), color=(200, 100, 50)).save(path, format="PNG")
    return path


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Create a PDF with document-info metadata."""
    path = tmp_path / "case.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.add_metadata(
        {
            "/Title": "ForenX Case PDF",
            "/Author": "ForenX Analyst",
            "/Creator": "ForenX Engine",
            "/Producer": "pypdf",
            "/Subject": "Phase 3 metadata test",
            "/Keywords": "forensics,metadata",
        }
    )
    with path.open("wb") as handle:
        writer.write(handle)
    return path


@pytest.fixture
def encrypted_pdf(tmp_path: Path) -> Path:
    """Create an encrypted PDF sample."""
    path = tmp_path / "secret.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_metadata({"/Title": "Encrypted Sample"})
    writer.encrypt("forenx-secret")
    with path.open("wb") as handle:
        writer.write(handle)
    return path


@pytest.fixture
def sample_docx(tmp_path: Path) -> Path:
    """Create a DOCX with core properties."""
    path = tmp_path / "report.docx"
    document = Document()
    document.core_properties.title = "ForenX DOCX Sample"
    document.core_properties.author = "ForenX Author"
    document.core_properties.subject = "Metadata extraction"
    document.core_properties.category = "Evidence"
    document.core_properties.last_modified_by = "ForenX Reviewer"
    document.core_properties.revision = 3
    document.core_properties.created = datetime(2024, 5, 1, 12, 0, tzinfo=timezone.utc)
    document.core_properties.modified = datetime(2024, 5, 2, 12, 0, tzinfo=timezone.utc)
    document.add_paragraph("Synthetic DOCX evidence for ForenX Phase 3 tests.")
    document.save(path)
    return path


class TestImageMetadata:
    """Image extractor tests."""

    def test_jpeg_with_exif(self, jpeg_with_exif: Path) -> None:
        """JPEG EXIF fields are extracted when present."""
        service = MetadataService()
        result = service.extract_image(jpeg_with_exif)
        assert result.filename == jpeg_with_exif.name
        assert result.extension == ".jpg"
        assert result.width == 32
        assert result.height == 24
        assert result.camera_make == "ForenXCam"
        assert result.camera_model == "FX-100"
        assert result.software == "ForenX Test Suite"
        assert result.orientation == 1
        assert result.date_taken is not None
        assert result.gps_latitude is None
        assert result.status in {MetadataStatus.SUCCESS, MetadataStatus.PARTIAL}

    def test_png_without_exif(self, png_without_exif: Path) -> None:
        """PNG without EXIF still returns dimensions and None EXIF fields."""
        result = MetadataService().extract_image(png_without_exif)
        assert result.width == 16
        assert result.height == 10
        assert result.camera_make is None
        assert result.camera_model is None
        assert result.date_taken is None
        assert result.status == MetadataStatus.PARTIAL


class TestPdfMetadata:
    """PDF extractor tests."""

    def test_pdf_metadata(self, sample_pdf: Path) -> None:
        """PDF document-info fields and page count are extracted."""
        result = MetadataService().extract_pdf(sample_pdf)
        assert result.file_name == sample_pdf.name
        assert result.title == "ForenX Case PDF"
        assert result.author == "ForenX Analyst"
        assert result.creator == "ForenX Engine"
        assert result.producer == "pypdf"
        assert result.subject == "Phase 3 metadata test"
        assert result.page_count == 1
        assert result.encrypted is False

    def test_encrypted_pdf(self, encrypted_pdf: Path) -> None:
        """Encrypted PDFs report encryption state without crashing."""
        result = MetadataService().extract_pdf(encrypted_pdf)
        assert result.encrypted is True
        assert result.file_name == encrypted_pdf.name


class TestDocumentMetadata:
    """DOCX extractor tests."""

    def test_docx_metadata(self, sample_docx: Path) -> None:
        """DOCX core properties are extracted."""
        result = MetadataService().extract_document(sample_docx)
        assert result.file_name == sample_docx.name
        assert result.title == "ForenX DOCX Sample"
        assert result.author == "ForenX Author"
        assert result.subject == "Metadata extraction"
        assert result.category == "Evidence"
        assert result.last_modified_by == "ForenX Reviewer"
        assert result.revision is not None
        assert result.created_date is not None
        assert result.modified_date is not None


class TestFilesystemMetadata:
    """Filesystem extractor tests."""

    def test_filesystem_metadata(self, png_without_exif: Path) -> None:
        """Filesystem metadata includes SHA256 from HashService."""
        result = MetadataService().extract_filesystem(png_without_exif)
        assert result.file_name == png_without_exif.name
        assert result.absolute_path == str(png_without_exif.resolve())
        assert result.extension == ".png"
        assert result.file_size == png_without_exif.stat().st_size
        assert result.readable is True
        assert result.sha256 == generate_sha256(png_without_exif)
        assert result.created_time is not None
        assert result.modified_time is not None


class TestServiceDispatch:
    """MetadataService / dispatcher tests."""

    def test_detect_and_extract_image(self, png_without_exif: Path) -> None:
        """extract() dispatches image files and includes filesystem data."""
        assert detect_file_type(png_without_exif).value == "image"
        result = MetadataService().extract(png_without_exif)
        assert result.file_type == "image"
        assert result.image is not None
        assert result.filesystem is not None
        assert result.pdf is None
        assert result.document is None

    def test_detect_and_extract_pdf(self, sample_pdf: Path) -> None:
        """extract() dispatches PDF files."""
        result = extract_metadata(sample_pdf)
        assert result.file_type == "pdf"
        assert result.pdf is not None
        assert result.pdf.page_count == 1

    def test_detect_and_extract_docx(self, sample_docx: Path) -> None:
        """extract() dispatches DOCX files."""
        result = MetadataService().extract(sample_docx)
        assert result.file_type == "docx"
        assert result.document is not None
        assert result.document.title == "ForenX DOCX Sample"

    def test_missing_file(self, tmp_path: Path) -> None:
        """Missing files raise EvidenceFileError."""
        with pytest.raises(EvidenceFileError):
            MetadataService().extract(tmp_path / "missing.jpg")

    def test_unsupported_extension(self, tmp_path: Path) -> None:
        """Unsupported specialized types raise UnsupportedFileTypeError."""
        path = tmp_path / "notes.txt"
        path.write_text("not supported by extract()", encoding="utf-8")
        with pytest.raises(UnsupportedFileTypeError):
            MetadataService().extract(path)

    def test_filesystem_allows_unsupported_specialized_type(
        self,
        tmp_path: Path,
    ) -> None:
        """extract_filesystem works for any readable file."""
        path = tmp_path / "notes.txt"
        path.write_text("filesystem only", encoding="utf-8")
        result = MetadataService().extract_filesystem(path)
        assert result.extension == ".txt"
        assert result.sha256 == generate_sha256(path)

    def test_invalid_image_raises(self, tmp_path: Path) -> None:
        """Corrupt image content raises MetadataExtractionError."""
        path = tmp_path / "broken.jpg"
        path.write_bytes(b"not-an-image")
        with pytest.raises(MetadataExtractionError):
            MetadataService().extract_image(path)
