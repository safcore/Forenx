"""Integrity checking for forensic evidence files."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.hashing.hash_generator import compute_hash, normalize_algorithm, resolve_evidence_path
from app.hashing.hash_verifier import normalize_hash_digest
from app.schemas.hash import IntegrityResult, IntegrityStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


def check_integrity(
    file_path: str | Path,
    original_hash: str,
    algorithm: str,
) -> IntegrityResult:
    """Compare a file against an original known-good hash.

    Args:
        file_path: Path to the evidence file.
        original_hash: Original digest captured at intake / acquisition.
        algorithm: Hash algorithm (``md5``, ``sha1``, or ``sha256``).

    Returns:
        ``IntegrityResult`` with status ``PASS`` or ``FAIL``.
    """
    path = resolve_evidence_path(file_path)
    normalized_algorithm = normalize_algorithm(algorithm)
    normalized_original = normalize_hash_digest(original_hash)

    logger.info(
        "Starting integrity check for '%s' using algorithm=%s",
        path.name,
        normalized_algorithm,
    )

    computed_hash = compute_hash(path, normalized_algorithm)
    passed = computed_hash == normalized_original
    status = IntegrityStatus.PASS if passed else IntegrityStatus.FAIL
    timestamp = datetime.now(timezone.utc)
    file_size = path.stat().st_size

    if passed:
        message = "Integrity check PASSED"
        logger.info(
            "Integrity result for '%s': status=PASS algorithm=%s",
            path.name,
            normalized_algorithm,
        )
    else:
        message = "Integrity check FAILED: digest mismatch"
        logger.warning(
            "Integrity result for '%s': status=FAIL algorithm=%s",
            path.name,
            normalized_algorithm,
        )

    return IntegrityResult(
        file_name=path.name,
        file_size=file_size,
        algorithm=normalized_algorithm,
        hash=computed_hash,
        original_hash=normalized_original,
        computed_hash=computed_hash,
        status=status,
        verified=passed,
        timestamp=timestamp,
        message=message,
    )
