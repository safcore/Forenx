"""Pydantic schemas for hash computation, verification, and integrity checks."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class IntegrityStatus(str, Enum):
    """Possible outcomes of an evidence integrity check."""

    PASS = "PASS"
    FAIL = "FAIL"


class HashResult(BaseModel):
    """Result of a single hash computation for an evidence file.

    Attributes:
        file_name: Basename of the hashed evidence file.
        file_size: Size of the file in bytes.
        algorithm: Canonical algorithm name (md5, sha1, sha256).
        hash: Lowercase hexadecimal digest.
        timestamp: UTC time when the digest was computed.
        message: Optional human-readable status message.
    """

    file_name: str
    file_size: int = Field(ge=0)
    algorithm: str
    hash: str
    timestamp: datetime
    message: str = "Hash computed successfully"


class HashVerificationResult(BaseModel):
    """Result of comparing a file digest against an expected value.

    Attributes:
        file_name: Basename of the evidence file.
        file_size: Size of the file in bytes.
        algorithm: Canonical algorithm name.
        hash: Computed lowercase hexadecimal digest (alias of computed_hash).
        expected_hash: Digest supplied by the caller.
        computed_hash: Digest computed from the file.
        verified: Whether expected and computed digests match.
        timestamp: UTC time when verification completed.
        message: Human-readable outcome description.
    """

    file_name: str
    file_size: int = Field(ge=0)
    algorithm: str
    hash: str
    expected_hash: str
    computed_hash: str
    verified: bool
    timestamp: datetime
    message: str


class IntegrityResult(BaseModel):
    """Result of an evidence integrity check against an original hash.

    Attributes:
        file_name: Basename of the evidence file.
        file_size: Size of the file in bytes.
        algorithm: Canonical algorithm name.
        hash: Computed lowercase hexadecimal digest.
        original_hash: Original known-good digest.
        computed_hash: Digest computed from the current file.
        status: ``PASS`` or ``FAIL``.
        verified: Convenience boolean mirroring a passing status.
        timestamp: UTC time when the check completed.
        message: Human-readable outcome description.
    """

    file_name: str
    file_size: int = Field(ge=0)
    algorithm: str
    hash: str
    original_hash: str
    computed_hash: str
    status: IntegrityStatus
    verified: bool
    timestamp: datetime
    message: str
