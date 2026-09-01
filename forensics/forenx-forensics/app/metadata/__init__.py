"""Metadata extraction package for the ForenX forensics engine.

Public helpers:

- ``extract_metadata`` / specialized extractors
- ``detect_file_type``
"""

from app.metadata.document_metadata import extract_document_metadata
from app.metadata.extractor import detect_file_type, extract_metadata
from app.metadata.filesystem_metadata import extract_filesystem_metadata
from app.metadata.image_metadata import extract_image_metadata
from app.metadata.pdf_metadata import extract_pdf_metadata

__all__ = [
    "detect_file_type",
    "extract_metadata",
    "extract_image_metadata",
    "extract_pdf_metadata",
    "extract_document_metadata",
    "extract_filesystem_metadata",
]
