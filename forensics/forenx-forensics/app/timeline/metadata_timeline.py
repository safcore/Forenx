"""Convert Phase 3 metadata timestamps into timeline events.

Does not invent timestamps when embedded metadata fields are absent.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.hashing.hash_generator import resolve_evidence_path
from app.schemas.metadata import (
    DocumentMetadata,
    ImageMetadata,
    MetadataResult,
    PdfMetadata,
)
from app.schemas.timeline import TimelineEvent, TimelineEventType, TimestampType
from app.services.metadata_service import MetadataService
from app.timeline.event_normalizer import normalize_candidates
from app.timeline.models import RawTimelineCandidate, metadata_source_label
from app.utils.exceptions import (
    EvidenceFileError,
    MetadataExtractionError,
    UnsupportedFileTypeError,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _image_candidates(
    path: Path,
    image: ImageMetadata,
) -> list[RawTimelineCandidate]:
    source_file = str(path.resolve(strict=False))
    meta: dict[str, Any] = {
        "filename": image.filename,
        "camera_make": image.camera_make,
        "camera_model": image.camera_model,
    }
    return [
        RawTimelineCandidate(
            raw_timestamp=image.date_taken,
            timestamp_type=TimestampType.CREATED,
            event_type=TimelineEventType.METADATA_CREATED,
            source=metadata_source_label("image"),
            source_file=source_file,
            description=f"Image captured/taken metadata for {path.name}",
            artifact="metadata.image.date_taken",
            path=source_file,
            metadata=meta,
            base_confidence=0.85,
        )
    ]


def _pdf_candidates(path: Path, pdf: PdfMetadata) -> list[RawTimelineCandidate]:
    source_file = str(path.resolve(strict=False))
    base = {
        "file_name": pdf.file_name,
        "title": pdf.title,
        "author": pdf.author,
    }
    return [
        RawTimelineCandidate(
            raw_timestamp=pdf.creation_date,
            timestamp_type=TimestampType.CREATED,
            event_type=TimelineEventType.METADATA_CREATED,
            source=metadata_source_label("pdf"),
            source_file=source_file,
            description=f"PDF creation metadata for {path.name}",
            artifact="metadata.pdf.creation_date",
            path=source_file,
            metadata=base,
            base_confidence=0.85,
        ),
        RawTimelineCandidate(
            raw_timestamp=pdf.modification_date,
            timestamp_type=TimestampType.MODIFIED,
            event_type=TimelineEventType.METADATA_MODIFIED,
            source=metadata_source_label("pdf"),
            source_file=source_file,
            description=f"PDF modification metadata for {path.name}",
            artifact="metadata.pdf.modification_date",
            path=source_file,
            metadata=base,
            base_confidence=0.85,
        ),
    ]


def _docx_candidates(
    path: Path,
    document: DocumentMetadata,
) -> list[RawTimelineCandidate]:
    source_file = str(path.resolve(strict=False))
    base = {
        "file_name": document.file_name,
        "title": document.title,
        "author": document.author,
    }
    return [
        RawTimelineCandidate(
            raw_timestamp=document.created_date,
            timestamp_type=TimestampType.CREATED,
            event_type=TimelineEventType.METADATA_CREATED,
            source=metadata_source_label("docx"),
            source_file=source_file,
            description=f"DOCX created metadata for {path.name}",
            artifact="metadata.docx.created_date",
            path=source_file,
            metadata=base,
            base_confidence=0.85,
        ),
        RawTimelineCandidate(
            raw_timestamp=document.modified_date,
            timestamp_type=TimestampType.MODIFIED,
            event_type=TimelineEventType.METADATA_MODIFIED,
            source=metadata_source_label("docx"),
            source_file=source_file,
            description=f"DOCX modified metadata for {path.name}",
            artifact="metadata.docx.modified_date",
            path=source_file,
            metadata=base,
            base_confidence=0.85,
        ),
    ]


def extract_metadata_events_from_result(
    path: str | Path,
    result: MetadataResult,
) -> tuple[list[TimelineEvent], list[str]]:
    """Build timeline events from an already-extracted ``MetadataResult``."""
    file_path = Path(path)
    candidates: list[RawTimelineCandidate] = []
    if result.image is not None:
        candidates.extend(_image_candidates(file_path, result.image))
    if result.pdf is not None:
        candidates.extend(_pdf_candidates(file_path, result.pdf))
    if result.document is not None:
        candidates.extend(_docx_candidates(file_path, result.document))
    return normalize_candidates(candidates)


def extract_metadata_events(
    file_path: str | Path,
    *,
    metadata_service: MetadataService | None = None,
) -> tuple[list[TimelineEvent], list[str]]:
    """Extract embedded metadata timestamps for a supported evidence file.

    Unsupported file types return an empty event list (not an error).
    """
    path = resolve_evidence_path(file_path)
    logger.info("Metadata timeline extraction started for '%s'", path.name)
    service = metadata_service or MetadataService()
    warnings: list[str] = []

    try:
        result = service.extract(path)
    except UnsupportedFileTypeError:
        logger.info(
            "No metadata timeline events for unsupported type '%s'",
            path.name,
        )
        return [], warnings
    except (EvidenceFileError, MetadataExtractionError) as exc:
        warning = f"Metadata timeline skipped for '{path.name}': {exc}"
        warnings.append(warning)
        logger.warning(warning)
        return [], warnings

    events, normalize_warnings = extract_metadata_events_from_result(path, result)
    warnings.extend(normalize_warnings)
    logger.info(
        "Metadata timeline extraction finished for '%s' events=%d",
        path.name,
        len(events),
    )
    return events, warnings
