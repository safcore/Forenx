"""Filesystem metadata extraction for forensic evidence files."""

from __future__ import annotations

import mimetypes
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from app.hashing.hash_generator import generate_sha256, resolve_evidence_path
from app.schemas.metadata import FileMetadata, MetadataStatus
from app.utils.exceptions import EvidenceFileError, ForenXError, MetadataExtractionError
from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.services.hash_service import HashService

logger = get_logger(__name__)


def _to_utc(timestamp: float | None) -> datetime | None:
    """Convert a POSIX timestamp to an aware UTC datetime.

    Args:
        timestamp: Seconds since the epoch, or ``None``.

    Returns:
        Timezone-aware UTC datetime, or ``None`` when unavailable.
    """
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def _is_hidden(path: Path) -> bool:
    """Determine whether a file is hidden on the host platform.

    Args:
        path: Path to inspect.

    Returns:
        ``True`` if the file is hidden; otherwise ``False``.
    """
    if path.name.startswith("."):
        return True

    if sys.platform == "win32":
        try:
            import ctypes

            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            # INVALID_FILE_ATTRIBUTES == -1
            if attrs == -1:
                return False
            FILE_ATTRIBUTE_HIDDEN = 0x2
            return bool(attrs & FILE_ATTRIBUTE_HIDDEN)
        except (AttributeError, OSError, ValueError):
            return False

    return False


def extract_filesystem_metadata(
    file_path: str | Path,
    *,
    hash_service: HashService | None = None,
) -> FileMetadata:
    """Extract filesystem metadata for an evidence file.

    Args:
        file_path: Path to the evidence file.
        hash_service: Optional ``HashService`` for SHA256. When omitted,
            SHA256 is computed via the hashing module directly (avoids a
            feature→service dependency).

    Returns:
        Populated ``FileMetadata`` model.

    Raises:
        EvidenceFileError: If the path is empty, missing, or inaccessible.
        MetadataExtractionError: If metadata collection fails unexpectedly.
    """
    path = resolve_evidence_path(file_path)
    logger.info("Filesystem metadata extraction started for '%s'", path.name)

    try:
        stats = path.stat()
    except PermissionError as exc:
        raise EvidenceFileError(
            f"Permission denied while reading filesystem metadata: {path}"
        ) from exc
    except OSError as exc:
        raise MetadataExtractionError(
            f"Failed to stat evidence file '{path}': {exc}"
        ) from exc

    created = getattr(stats, "st_birthtime", None)
    if created is None:
        created = stats.st_ctime

    sha256: str | None
    try:
        if hash_service is not None:
            hash_results = hash_service.calculate_hashes(path)
            sha256 = next(
                (item.hash for item in hash_results if item.algorithm == "sha256"),
                None,
            )
        else:
            sha256 = generate_sha256(path)
    except (ForenXError, OSError) as exc:
        logger.warning(
            "SHA256 computation failed for '%s': %s",
            path.name,
            exc,
        )
        sha256 = None

    mime_type, _ = mimetypes.guess_type(str(path))
    status = MetadataStatus.SUCCESS if sha256 else MetadataStatus.PARTIAL
    message = (
        "Filesystem metadata extracted successfully"
        if sha256
        else "Filesystem metadata extracted; SHA256 unavailable"
    )

    result = FileMetadata(
        timestamp=datetime.now(timezone.utc),
        status=status,
        message=message,
        file_name=path.name,
        absolute_path=str(path.resolve()),
        extension=path.suffix.lower(),
        mime_type=mime_type,
        file_size=stats.st_size,
        created_time=_to_utc(created),
        modified_time=_to_utc(stats.st_mtime),
        accessed_time=_to_utc(stats.st_atime),
        readable=os.access(path, os.R_OK),
        writable=os.access(path, os.W_OK),
        hidden=_is_hidden(path),
        sha256=sha256,
    )
    logger.info("Filesystem metadata extraction succeeded for '%s'", path.name)
    return result
