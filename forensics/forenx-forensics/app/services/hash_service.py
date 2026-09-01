"""Hashing service orchestration for the ForenX forensics engine.

Provides the public Phase 2 API for streaming MD5 / SHA1 / SHA256 generation,
hash verification, and integrity PASS/FAIL checks against evidence files.

Typical usage example:

    from app.services.hash_service import HashService

    results = HashService().calculate_hashes("evidence/sample_case/sample_evidence.txt")
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.hashing.hash_generator import generate_all_hashes, resolve_evidence_path
from app.hashing.hash_verifier import verify_hash
from app.hashing.integrity_checker import check_integrity
from app.schemas.hash import HashResult, HashVerificationResult, IntegrityResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class HashService:
    """High-level API for evidence hashing, verification, and integrity checks.

    Designed for reuse by CLI tools, tests, and a future Django backend.
    """

    def __init__(self) -> None:
        """Initialize the hashing service."""

    def calculate_hashes(self, file_path: str | Path) -> list[HashResult]:
        """Calculate MD5, SHA1, and SHA256 digests for an evidence file.

        Digests are computed in a single streaming pass over the file.

        Args:
            file_path: Path to the evidence file.

        Returns:
            List of ``HashResult`` models (one per algorithm).
        """
        path = resolve_evidence_path(file_path)
        logger.info("HashService.calculate_hashes started for '%s'", path.name)

        digests = generate_all_hashes(path)
        timestamp = datetime.now(timezone.utc)
        file_size = path.stat().st_size

        results = [
            HashResult(
                file_name=path.name,
                file_size=file_size,
                algorithm=algorithm,
                hash=digest,
                timestamp=timestamp,
                message="Hash computed successfully",
            )
            for algorithm, digest in digests.items()
        ]

        logger.info(
            "HashService.calculate_hashes completed for '%s' (%d algorithms)",
            path.name,
            len(results),
        )
        return results

    def verify(
        self,
        file_path: str | Path,
        expected_hash: str,
        algorithm: str,
    ) -> HashVerificationResult:
        """Verify an evidence file against an expected digest.

        Args:
            file_path: Path to the evidence file.
            expected_hash: Expected hexadecimal digest.
            algorithm: Hash algorithm name.

        Returns:
            ``HashVerificationResult`` for the comparison.
        """
        logger.info(
            "HashService.verify started algorithm=%s file=%s",
            algorithm,
            Path(file_path).name if file_path else "",
        )
        result = verify_hash(file_path, expected_hash, algorithm)
        logger.info(
            "HashService.verify finished verified=%s algorithm=%s",
            result.verified,
            result.algorithm,
        )
        return result

    def integrity_check(
        self,
        file_path: str | Path,
        original_hash: str,
        algorithm: str,
    ) -> IntegrityResult:
        """Run an integrity check against an original known-good digest.

        Args:
            file_path: Path to the evidence file.
            original_hash: Original hexadecimal digest.
            algorithm: Hash algorithm name.

        Returns:
            ``IntegrityResult`` with status ``PASS`` or ``FAIL``.
        """
        logger.info(
            "HashService.integrity_check started algorithm=%s file=%s",
            algorithm,
            Path(file_path).name if file_path else "",
        )
        result = check_integrity(file_path, original_hash, algorithm)
        logger.info(
            "HashService.integrity_check finished status=%s algorithm=%s",
            result.status.value,
            result.algorithm,
        )
        return result
