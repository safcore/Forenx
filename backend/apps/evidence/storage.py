import re
import uuid
from pathlib import Path

from django.conf import settings
from rest_framework.exceptions import ValidationError

_UNSAFE_NAME = re.compile(r"[^\w.\-()+ ]+", re.UNICODE)


def evidence_root() -> Path:
    """Return resolved evidence storage root, creating it if needed."""
    root = Path(settings.EVIDENCE_STORAGE_DIR).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def sanitize_original_filename(name: str) -> str:
    """Return a display-safe original filename (never used as a filesystem path)."""
    base = Path(str(name or "evidence.bin")).name
    cleaned = _UNSAFE_NAME.sub("_", base).strip(" .")
    return cleaned or "evidence.bin"


def assert_allowed_upload(original_filename: str, size: int) -> None:
    """Validate upload size and file extension against configured policies."""
    if size <= 0:
        raise ValidationError({"file": "Uploaded file is empty."})

    max_bytes = int(getattr(settings, "FORENX_MAX_UPLOAD_BYTES", 500 * 1024 * 1024))
    if size > max_bytes:
        raise ValidationError(
            {"file": f"Upload exceeds maximum size of {max_bytes} bytes."}
        )

    ext = Path(original_filename).suffix.lower()
    blocked_exts = set(
        getattr(
            settings,
            "FORENX_BLOCKED_EXTENSIONS",
            [".exe", ".bat", ".cmd", ".sh", ".msi"],
        )
    )
    if ext in blocked_exts:
        raise ValidationError(
            {"file": f"File type '{ext}' is not allowed for evidence upload."}
        )


def build_storage_name(original_filename: str) -> str:
    """Generate a UUID-based disk storage filename preserving only the extension."""
    ext = Path(original_filename).suffix.lower()
    if len(ext) > 16:
        ext = ""
    return f"{uuid.uuid4().hex}{ext}"


def resolve_safe_path(root: Path, storage_name: str) -> Path:
    """Resolve a target path under root and reject traversal attempts."""
    if (
        not storage_name
        or "\x00" in storage_name
        or storage_name != Path(storage_name).name
    ):
        raise ValidationError({"file": "Invalid storage name."})

    if ".." in storage_name or "/" in storage_name or "\\" in storage_name:
        raise ValidationError({"file": "Path traversal is not allowed."})

    target = (root / storage_name).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise ValidationError(
            {"file": "Resolved path escapes the storage root."}
        ) from exc

    return target


def store_uploaded_file(uploaded_file, *, original_filename: str) -> tuple[str, Path, int]:
    """Persist an uploaded file under the evidence storage root.

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
        raise ValidationError({"file": "Generated storage path already exists."})

    written = 0
    with path.open("wb") as handle:
        for chunk in uploaded_file.chunks():
            handle.write(chunk)
            written += len(chunk)

    if written <= 0:
        path.unlink(missing_ok=True)
        raise ValidationError({"file": "Uploaded file is empty."})

    return storage_name, path, written


def delete_storage_file(stored_path: str | Path | None) -> None:
    """Best-effort cleanup of an evidence file upon failure."""
    if not stored_path:
        return
    try:
        Path(stored_path).unlink(missing_ok=True)
    except Exception:
        pass
