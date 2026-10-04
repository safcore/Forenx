import logging
import re
import uuid
from pathlib import Path

from django.conf import settings
from rest_framework.exceptions import NotFound, ValidationError

logger = logging.getLogger(__name__)

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


def is_supabase_storage_enabled() -> bool:
    """Determine whether Supabase Storage backend is configured and enabled."""
    url = getattr(settings, "SUPABASE_URL", None)
    key = getattr(settings, "SUPABASE_SECRET_KEY", None)
    backend = getattr(settings, "FORENX_STORAGE_BACKEND", "local")
    return bool(url and key and str(backend).lower() == "supabase")


def get_supabase_client():
    """Initialize or return Supabase client using server-side credentials."""
    url = getattr(settings, "SUPABASE_URL", None)
    key = getattr(settings, "SUPABASE_SECRET_KEY", None)
    if not url or not key:
        raise ValidationError(
            {"detail": "Supabase Storage credentials are not configured."}
        )
    from supabase import create_client

    return create_client(str(url), str(key))


def get_supabase_bucket_name() -> str:
    """Return configured private evidence bucket name."""
    return str(getattr(settings, "SUPABASE_STORAGE_BUCKET", "evidence") or "evidence")


def upload_evidence_to_supabase(
    local_path: Path,
    storage_name: str,
    mime_type: str = "application/octet-stream",
) -> None:
    """Upload a locally staged evidence file to the private Supabase storage bucket."""
    if not is_supabase_storage_enabled():
        return

    client = get_supabase_client()
    bucket = get_supabase_bucket_name()
    try:
        with local_path.open("rb") as handle:
            client.storage.from_(bucket).upload(
                path=storage_name,
                file=handle,
                file_options={"content-type": mime_type, "upsert": "true"},
            )
    except Exception as exc:
        logger.error("Failed to upload evidence to Supabase Storage: %s", exc)
        raise ValidationError(
            {"file": "Failed to persist evidence to cloud storage."}
        ) from exc


def download_evidence_from_supabase(storage_name: str, target_path: Path) -> Path:
    """Download an evidence object from Supabase Storage into a local file path."""
    if not is_supabase_storage_enabled():
        raise NotFound("Persistent cloud storage is not configured.")

    client = get_supabase_client()
    bucket = get_supabase_bucket_name()
    try:
        data = client.storage.from_(bucket).download(storage_name)
    except Exception as exc:
        logger.error("Failed to download evidence from Supabase Storage: %s", exc)
        raise NotFound(
            "Evidence file could not be retrieved from persistent storage."
        ) from exc

    if not data:
        raise NotFound(
            "Evidence file could not be retrieved from persistent storage."
        )

    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_target = target_path.with_suffix(f"{target_path.suffix}.tmp")
    try:
        with temp_target.open("wb") as handle:
            handle.write(data)
        temp_target.replace(target_path)
    except Exception as exc:
        temp_target.unlink(missing_ok=True)
        logger.error("Failed to write downloaded evidence locally: %s", exc)
        raise NotFound(
            "Evidence file could not be retrieved from persistent storage."
        ) from exc

    return target_path


def is_evidence_in_supabase(storage_name: str) -> bool:
    """Check whether an evidence object exists in the private Supabase bucket."""
    if not is_supabase_storage_enabled() or not storage_name:
        return False

    try:
        client = get_supabase_client()
        bucket = get_supabase_bucket_name()
        return bool(client.storage.from_(bucket).exists(storage_name))
    except Exception as exc:
        logger.debug("Supabase existence check failed: %s", exc)
        return False


def delete_supabase_file(storage_name: str) -> None:
    """Best-effort deletion of an evidence object from the Supabase bucket."""
    if not is_supabase_storage_enabled() or not storage_name:
        return

    try:
        client = get_supabase_client()
        bucket = get_supabase_bucket_name()
        client.storage.from_(bucket).remove([storage_name])
    except Exception as exc:
        logger.warning("Failed to delete evidence object from Supabase Storage: %s", exc)


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


def delete_storage_file(
    stored_path: str | Path | None,
    storage_name: str | None = None,
) -> None:
    """Best-effort cleanup of an evidence file on local disk and Supabase Storage."""
    if stored_path:
        try:
            Path(stored_path).unlink(missing_ok=True)
        except Exception:
            pass

    s_name = storage_name or (Path(stored_path).name if stored_path else None)
    if s_name and is_supabase_storage_enabled():
        delete_supabase_file(s_name)


def ensure_local_evidence_file(evidence) -> Path:
    """Ensure an evidence file is available locally for hashing or analysis.

    1. Checks if the file at evidence.stored_path exists on local disk.
    2. If missing, checks if the file exists under evidence_root() with evidence.storage_name.
    3. If still missing and Supabase is enabled, downloads the object from Supabase.
    4. Returns the validated local Path.
    5. If missing and cannot be retrieved, raises NotFound.
    """
    # 1. Existing stored_path check
    if getattr(evidence, "stored_path", None):
        local_path = Path(evidence.stored_path)
        if local_path.is_file() and local_path.stat().st_size > 0:
            return local_path

    # 2. Check standard location under evidence_root
    storage_name = getattr(evidence, "storage_name", None)
    if not storage_name:
        raise NotFound("Evidence file is missing storage identifier.")

    root = evidence_root()
    expected_path = resolve_safe_path(root, storage_name)
    if expected_path.is_file() and expected_path.stat().st_size > 0:
        return expected_path

    # 3. Retrieve from Supabase if enabled
    if is_supabase_storage_enabled():
        return download_evidence_from_supabase(storage_name, expected_path)

    raise NotFound("Evidence file is missing from physical storage.")


def is_storage_available(evidence) -> bool:
    """Check whether the evidence file exists locally or in Supabase Storage."""
    try:
        if getattr(evidence, "stored_path", None) and Path(evidence.stored_path).is_file():
            return True
        root = evidence_root()
        storage_name = getattr(evidence, "storage_name", None)
        if storage_name and (root / storage_name).is_file():
            return True
    except Exception:
        pass

    if is_supabase_storage_enabled():
        storage_name = getattr(evidence, "storage_name", None)
        if storage_name:
            return is_evidence_in_supabase(storage_name)

    return False
