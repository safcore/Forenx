"""Evidence file hashing utilities.

Provides streaming MD5, SHA1, and SHA256 generators suitable for large
forensic evidence files without loading them entirely into memory.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path

from app.utils.config import HASH_CHUNK_SIZE, SUPPORTED_HASH_ALGORITHMS
from app.utils.exceptions import (
    EvidenceFileError,
    UnsupportedAlgorithmError,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

_HASHLIB_NAMES: dict[str, str] = {
    "md5": "md5",
    "sha1": "sha1",
    "sha256": "sha256",
}


def normalize_algorithm(algorithm: str) -> str:
    """Normalize and validate a hash algorithm name.

    Args:
        algorithm: Algorithm name (case-insensitive), e.g. ``\"SHA256\"``.

    Returns:
        Canonical lowercase algorithm name.

    Raises:
        UnsupportedAlgorithmError: If the algorithm is not supported.
        EvidenceFileError: If the algorithm string is empty.
    """
    if algorithm is None or not str(algorithm).strip():
        raise EvidenceFileError("Hash algorithm must not be empty")

    normalized = str(algorithm).strip().lower().replace("-", "")
    # Accept common aliases such as sha-256 -> sha256 after replace.
    if normalized not in SUPPORTED_HASH_ALGORITHMS:
        supported = ", ".join(sorted(SUPPORTED_HASH_ALGORITHMS))
        raise UnsupportedAlgorithmError(
            f"Unsupported hash algorithm '{algorithm}'. Supported: {supported}"
        )
    return normalized


def resolve_evidence_path(file_path: str | Path) -> Path:
    """Validate and resolve an evidence file path.

    Args:
        file_path: Path to the evidence file.

    Returns:
        Resolved ``Path`` pointing to an existing regular file.

    Raises:
        EvidenceFileError: If the path is empty, missing, not a file,
            or cannot be accessed due to permissions.
    """
    if file_path is None or (isinstance(file_path, str) and not file_path.strip()):
        raise EvidenceFileError("Evidence file path must not be empty")

    path = Path(file_path)

    try:
        if not path.exists():
            raise EvidenceFileError(f"Evidence file not found: {path}")
        if not path.is_file():
            raise EvidenceFileError(f"Evidence path is not a file: {path}")
    except PermissionError as exc:
        raise EvidenceFileError(
            f"Permission denied while accessing evidence file: {path}"
        ) from exc

    return path


def _iter_file_chunks(
    path: Path,
    chunk_size: int = HASH_CHUNK_SIZE,
) -> Iterable[bytes]:
    """Yield successive chunks from a file.

    Args:
        path: Path to an existing file.
        chunk_size: Number of bytes to read per iteration.

    Yields:
        Raw byte chunks from the file.

    Raises:
        EvidenceFileError: If the file cannot be opened or read.
    """
    if chunk_size <= 0:
        raise EvidenceFileError("Hash chunk size must be a positive integer")

    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    except PermissionError as exc:
        raise EvidenceFileError(
            f"Permission denied while reading evidence file: {path}"
        ) from exc
    except OSError as exc:
        raise EvidenceFileError(
            f"Failed to read evidence file '{path}': {exc}"
        ) from exc


def compute_hashes(
    file_path: str | Path,
    algorithms: Iterable[str] | None = None,
    *,
    chunk_size: int = HASH_CHUNK_SIZE,
) -> dict[str, str]:
    """Compute one or more digests for a file in a single pass.

    Args:
        file_path: Path to the evidence file.
        algorithms: Algorithms to compute. Defaults to MD5, SHA1, SHA256.
        chunk_size: Streaming read size in bytes.

    Returns:
        Mapping of algorithm name to lowercase hexadecimal digest.

    Raises:
        EvidenceFileError: If the path is invalid or unreadable.
        UnsupportedAlgorithmError: If an algorithm is not supported.
    """
    path = resolve_evidence_path(file_path)
    selected = (
        [normalize_algorithm(name) for name in algorithms]
        if algorithms is not None
        else sorted(SUPPORTED_HASH_ALGORITHMS)
    )

    if not selected:
        raise UnsupportedAlgorithmError("At least one hash algorithm is required")

    logger.info(
        "Starting hash computation for '%s' using algorithms=%s",
        path.name,
        ",".join(selected),
    )

    digesters = {
        name: hashlib.new(_HASHLIB_NAMES[name]) for name in selected
    }

    for chunk in _iter_file_chunks(path, chunk_size=chunk_size):
        for digester in digesters.values():
            digester.update(chunk)

    results = {name: digester.hexdigest().lower() for name, digester in digesters.items()}
    logger.info("Completed hash computation for '%s'", path.name)
    return results


def compute_hash(
    file_path: str | Path,
    algorithm: str,
    *,
    chunk_size: int = HASH_CHUNK_SIZE,
) -> str:
    """Compute a single digest for a file.

    Args:
        file_path: Path to the evidence file.
        algorithm: Hash algorithm name.
        chunk_size: Streaming read size in bytes.

    Returns:
        Lowercase hexadecimal digest string.
    """
    normalized = normalize_algorithm(algorithm)
    return compute_hashes(file_path, [normalized], chunk_size=chunk_size)[normalized]


def generate_md5(file_path: str | Path) -> str:
    """Generate an MD5 hash for ``file_path``.

    Args:
        file_path: Path to the evidence file.

    Returns:
        Lowercase hexadecimal MD5 digest.
    """
    return compute_hash(file_path, "md5")


def generate_sha1(file_path: str | Path) -> str:
    """Generate a SHA1 hash for ``file_path``.

    Args:
        file_path: Path to the evidence file.

    Returns:
        Lowercase hexadecimal SHA1 digest.
    """
    return compute_hash(file_path, "sha1")


def generate_sha256(file_path: str | Path) -> str:
    """Generate a SHA256 hash for ``file_path``.

    Args:
        file_path: Path to the evidence file.

    Returns:
        Lowercase hexadecimal SHA256 digest.
    """
    return compute_hash(file_path, "sha256")


def generate_all_hashes(file_path: str | Path) -> dict[str, str]:
    """Generate MD5, SHA1, and SHA256 hashes in a single file pass.

    Args:
        file_path: Path to the evidence file.

    Returns:
        Dictionary with keys ``md5``, ``sha1``, and ``sha256``.
    """
    return compute_hashes(file_path, ("md5", "sha1", "sha256"))
