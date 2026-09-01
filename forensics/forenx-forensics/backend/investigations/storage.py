"""Secure evidence file storage helpers."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from django.conf import settings

from investigations.api_errors import ApiError

_UNSAFE_NAME = re.compile(r"[^\w.\-()+ ]+", re.UNICODE)


def evidence_root() -> Path:
    root = Path(settings.EVIDENCE_STORAGE_DIR).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def report_root() -> Path:
    root = Path(settings.REPORT_STORAGE_DIR).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def sanitize_original_filename(name: str) -> str:
    """Return a display-safe original filename (never used as storage path)."""
    base = Path(str(name or "evidence.bin")).name
    cleaned = _UNSAFE_NAME.sub("_", base).strip(" .")
    return cleaned or "evidence.bin"


def assert_allowed_upload(original_filename: str, size: int) -> None:
    if size <= 0:
        raise ApiError("EMPTY_UPLOAD", "Uploaded file is empty.", http_status=400)
    max_bytes = int(settings.FORENX_MAX_UPLOAD_BYTES)
    if size > max_bytes:
        raise ApiError(
            "UPLOAD_TOO_LARGE",
            f"Upload exceeds maximum size of {max_bytes} bytes.",
            http_status=400,
        )
    ext = Path(original_filename).suffix.lower()
    if ext in set(settings.FORENX_BLOCKED_EXTENSIONS):
        raise ApiError(
            "BLOCKED_FILE_TYPE",
            f"File type '{ext}' is not allowed for evidence upload.",
            http_status=400,
        )


def build_storage_name(original_filename: str) -> str:
    """Generate a UUID-based storage name preserving only the extension."""
    ext = Path(original_filename).suffix.lower()
    if len(ext) > 16:
        ext = ""
    return f"{uuid.uuid4().hex}{ext}"


def resolve_safe_path(root: Path, storage_name: str) -> Path:
    """Resolve a path under root and reject traversal/escape attempts."""
    if (
        not storage_name
        or "\x00" in storage_name
        or storage_name != Path(storage_name).name
    ):
        raise ApiError("INVALID_STORAGE_NAME", "Invalid storage name.", http_status=400)
    if ".." in storage_name or "/" in storage_name or "\\" in storage_name:
        raise ApiError("PATH_TRAVERSAL", "Path traversal is not allowed.", http_status=400)
    target = (root / storage_name).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise ApiError(
            "PATH_TRAVERSAL",
            "Resolved path escapes the storage root.",
            http_status=400,
        ) from exc
    return target


def store_uploaded_file(uploaded_file, *, original_filename: str) -> tuple[str, Path, int]:
    """Persist an uploaded file under the evidence root.

    Returns:
        (storage_name, absolute_path, size_bytes)
    """
    safe_original = sanitize_original_filename(original_filename)
    size = int(getattr(uploaded_file, "size", 0) or 0)
    assert_allowed_upload(safe_original, size)

    root = evidence_root()
    storage_name = build_storage_name(safe_original)
    path = resolve_safe_path(root, storage_name)
    if path.exists():
        raise ApiError(
            "STORAGE_CONFLICT",
            "Generated storage path already exists.",
            http_status=409,
        )

    written = 0
    with path.open("wb") as handle:
        for chunk in uploaded_file.chunks():
            handle.write(chunk)
            written += len(chunk)

    if written <= 0:
        path.unlink(missing_ok=True)
        raise ApiError("EMPTY_UPLOAD", "Uploaded file is empty.", http_status=400)

    return storage_name, path, written


def delete_storage_file(stored_path: str | Path) -> None:
    """Best-effort cleanup for incomplete acquisitions."""
    path = Path(stored_path)
    try:
        root = evidence_root().resolve()
        resolved = path.resolve()
        resolved.relative_to(root)
        if resolved.is_file():
            resolved.unlink()
    except Exception:
        # Never raise during cleanup; caller already handling failure.
        return
