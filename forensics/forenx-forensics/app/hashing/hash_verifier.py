"""Hash verification for forensic evidence integrity checks."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.hashing.hash_generator import compute_hash, normalize_algorithm, resolve_evidence_path
from app.schemas.hash import HashVerificationResult
from app.utils.exceptions import InvalidHashError
from app.utils.logger import get_logger

logger = get_logger(__name__)


def normalize_hash_digest(expected_hash: str) -> str:
    """Validate and normalize an expected digest string.

    Args:
        expected_hash: Hexadecimal digest provided by the caller.

    Returns:
        Lowercase digest without surrounding whitespace.

    Raises:
        InvalidHashError: If the digest is empty or not hexadecimal.
    """
    if expected_hash is None or not str(expected_hash).strip():
        raise InvalidHashError("Expected hash must not be empty")

    normalized = str(expected_hash).strip().lower()
    if normalized.startswith("0x"):
        normalized = normalized[2:]

    try:
        int(normalized, 16)
    except ValueError as exc:
        raise InvalidHashError(
            f"Expected hash is not a valid hexadecimal digest: {expected_hash!r}"
        ) from exc

    if len(normalized) % 2 != 0:
        raise InvalidHashError(
            f"Expected hash has an invalid hexadecimal length: {expected_hash!r}"
        )

    return normalized


def verify_hash(
    file_path: str | Path,
    expected_hash: str,
    algorithm: str,
) -> HashVerificationResult:
    """Verify that a file matches an expected cryptographic hash.

    Args:
        file_path: Path to the evidence file.
        expected_hash: Expected lowercase or mixed-case hex digest.
        algorithm: Hash algorithm (``md5``, ``sha1``, or ``sha256``).

    Returns:
        ``HashVerificationResult`` describing the comparison outcome.
    """
    path = resolve_evidence_path(file_path)
    normalized_algorithm = normalize_algorithm(algorithm)
    normalized_expected = normalize_hash_digest(expected_hash)

    logger.info(
        "Starting hash verification for '%s' using algorithm=%s",
        path.name,
        normalized_algorithm,
    )

    computed_hash = compute_hash(path, normalized_algorithm)
    verified = computed_hash == normalized_expected
    timestamp = datetime.now(timezone.utc)
    file_size = path.stat().st_size

    if verified:
        message = "Hash verification succeeded"
        logger.info(
            "Hash verification result for '%s': verified=True algorithm=%s",
            path.name,
            normalized_algorithm,
        )
    else:
        message = "Hash verification failed: digest mismatch"
        logger.warning(
            "Hash verification result for '%s': verified=False algorithm=%s",
            path.name,
            normalized_algorithm,
        )

    return HashVerificationResult(
        file_name=path.name,
        file_size=file_size,
        algorithm=normalized_algorithm,
        hash=computed_hash,
        expected_hash=normalized_expected,
        computed_hash=computed_hash,
        verified=verified,
        timestamp=timestamp,
        message=message,
    )
