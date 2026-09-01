"""Image metadata extraction using Pillow."""

from __future__ import annotations

import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image, UnidentifiedImageError

from app.hashing.hash_generator import resolve_evidence_path
from app.schemas.metadata import ImageMetadata, MetadataStatus
from app.utils.config import SUPPORTED_IMAGE_EXTENSIONS
from app.utils.exceptions import (
    EvidenceFileError,
    MetadataExtractionError,
    UnsupportedFileTypeError,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

_EXIF_TAGS: dict[int, str] = {tag: name for name, tag in ExifTags.Base.__members__.items()}
_GPS_TAGS: dict[int, str] = {tag: name for name, tag in ExifTags.GPS.__members__.items()}


def _parse_exif_datetime(value: Any) -> datetime | None:
    """Parse common EXIF datetime string formats.

    Args:
        value: Raw EXIF datetime value.

    Returns:
        Aware UTC datetime when parsing succeeds; otherwise ``None``.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _ratio_to_float(value: Any) -> float | None:
    """Convert Pillow EXIF ratio-like values to float.

    Args:
        value: IFDRational or numeric component.

    Returns:
        Floating-point value, or ``None`` on failure.
    """
    try:
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _convert_gps_coordinate(values: Any, ref: str | None) -> float | None:
    """Convert GPS EXIF coordinates to decimal degrees.

    Args:
        values: Sequence of (degrees, minutes, seconds) ratios.
        ref: Hemisphere reference (N/S/E/W).

    Returns:
        Decimal degrees, or ``None`` when conversion is not possible.
    """
    try:
        degrees = _ratio_to_float(values[0])
        minutes = _ratio_to_float(values[1])
        seconds = _ratio_to_float(values[2])
    except (TypeError, IndexError, KeyError):
        return None

    if degrees is None or minutes is None or seconds is None:
        return None

    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
    if ref in {"S", "W"}:
        decimal = -decimal
    return decimal


def _extract_exif_map(image: Image.Image) -> dict[str, Any]:
    """Build a human-readable EXIF mapping from a Pillow image.

    Args:
        image: Opened Pillow image.

    Returns:
        Mapping of EXIF tag names to values. Empty when EXIF is absent.
    """
    try:
        raw = image.getexif()
    except Exception:  # noqa: BLE001 - EXIF absence is not fatal
        return {}

    if not raw:
        return {}

    decoded: dict[str, Any] = {}
    for tag_id, value in raw.items():
        name = _EXIF_TAGS.get(tag_id, str(tag_id))
        decoded[name] = value

    gps_ifd = raw.get_ifd(ExifTags.IFD.GPSInfo) if hasattr(raw, "get_ifd") else None
    if gps_ifd:
        gps_decoded: dict[str, Any] = {}
        for tag_id, value in gps_ifd.items():
            gps_decoded[_GPS_TAGS.get(tag_id, str(tag_id))] = value
        decoded["GPSInfo"] = gps_decoded

    return decoded


def extract_image_metadata(file_path: str | Path) -> ImageMetadata:
    """Extract forensic metadata from an image evidence file.

    Args:
        file_path: Path to a JPEG, PNG, TIFF, or BMP file.

    Returns:
        ``ImageMetadata`` with ``None`` for unavailable EXIF fields.

    Raises:
        EvidenceFileError: If the path is invalid or inaccessible.
        UnsupportedFileTypeError: If the extension is not supported.
        MetadataExtractionError: If the image cannot be opened/parsed.
    """
    path = resolve_evidence_path(file_path)
    extension = path.suffix.lower()
    if extension not in SUPPORTED_IMAGE_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_IMAGE_EXTENSIONS))
        raise UnsupportedFileTypeError(
            f"Unsupported image type '{extension}'. Supported: {supported}"
        )

    logger.info("Image metadata extraction started for '%s'", path.name)

    try:
        with Image.open(path) as image:
            image.load()
            width, height = image.size
            color_mode = image.mode
            exif = _extract_exif_map(image)
    except PermissionError as exc:
        raise EvidenceFileError(
            f"Permission denied while reading image metadata: {path}"
        ) from exc
    except UnidentifiedImageError as exc:
        raise MetadataExtractionError(
            f"Invalid or unreadable image document: {path}"
        ) from exc
    except OSError as exc:
        raise MetadataExtractionError(
            f"Failed to extract image metadata from '{path}': {exc}"
        ) from exc

    gps = exif.get("GPSInfo") if isinstance(exif.get("GPSInfo"), dict) else {}
    latitude = (
        _convert_gps_coordinate(gps.get("GPSLatitude"), gps.get("GPSLatitudeRef"))
        if gps
        else None
    )
    longitude = (
        _convert_gps_coordinate(gps.get("GPSLongitude"), gps.get("GPSLongitudeRef"))
        if gps
        else None
    )

    mime_type, _ = mimetypes.guess_type(str(path))
    date_taken = _parse_exif_datetime(
        exif.get("DateTimeOriginal") or exif.get("DateTime")
    )
    orientation = exif.get("Orientation")
    if orientation is not None:
        try:
            orientation = int(orientation)
        except (TypeError, ValueError):
            orientation = None

    has_exif = bool(exif)
    status = MetadataStatus.SUCCESS if has_exif else MetadataStatus.PARTIAL
    message = (
        "Image metadata extracted successfully"
        if has_exif
        else "Image metadata extracted; EXIF data unavailable"
    )

    result = ImageMetadata(
        timestamp=datetime.now(timezone.utc),
        status=status,
        message=message,
        filename=path.name,
        extension=extension,
        mime_type=mime_type,
        file_size=path.stat().st_size,
        width=width,
        height=height,
        camera_make=_as_optional_str(exif.get("Make")),
        camera_model=_as_optional_str(exif.get("Model")),
        software=_as_optional_str(exif.get("Software")),
        date_taken=date_taken,
        gps_latitude=latitude,
        gps_longitude=longitude,
        orientation=orientation,
        color_mode=color_mode,
    )
    logger.info("Image metadata extraction succeeded for '%s'", path.name)
    return result


def _as_optional_str(value: Any) -> str | None:
    """Normalize EXIF text fields to stripped strings or ``None``."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None
