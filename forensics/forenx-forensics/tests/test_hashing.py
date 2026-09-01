"""Comprehensive tests for Phase 2 evidence hashing and integrity."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.hashing.hash_generator import (
    generate_all_hashes,
    generate_md5,
    generate_sha1,
    generate_sha256,
)
from app.hashing.hash_verifier import verify_hash
from app.hashing.integrity_checker import check_integrity
from app.schemas.hash import IntegrityStatus
from app.services.hash_service import HashService
from app.utils.exceptions import (
    EvidenceFileError,
    InvalidHashError,
    UnsupportedAlgorithmError,
)


@pytest.fixture
def text_file(tmp_path: Path) -> Path:
    """Create a small UTF-8 text evidence file."""
    path = tmp_path / "note.txt"
    path.write_text("ForenX integrity sample\n", encoding="utf-8")
    return path


@pytest.fixture
def binary_file(tmp_path: Path) -> Path:
    """Create a small binary evidence file."""
    path = tmp_path / "blob.bin"
    path.write_bytes(bytes(range(256)) + b"\x00\xffForenX")
    return path


@pytest.fixture
def empty_file(tmp_path: Path) -> Path:
    """Create an empty evidence file."""
    path = tmp_path / "empty.dat"
    path.write_bytes(b"")
    return path


def _reference_digest(path: Path, algorithm: str) -> str:
    """Compute a reference digest with hashlib for assertions."""
    digester = hashlib.new(algorithm)
    digester.update(path.read_bytes())
    return digester.hexdigest().lower()


class TestHashGenerator:
    """Tests for streaming hash generation helpers."""

    def test_generate_md5_text_file(self, text_file: Path) -> None:
        """MD5 matches the reference digest for a text file."""
        assert generate_md5(text_file) == _reference_digest(text_file, "md5")

    def test_generate_sha1_text_file(self, text_file: Path) -> None:
        """SHA1 matches the reference digest for a text file."""
        assert generate_sha1(text_file) == _reference_digest(text_file, "sha1")

    def test_generate_sha256_text_file(self, text_file: Path) -> None:
        """SHA256 matches the reference digest for a text file."""
        assert generate_sha256(text_file) == _reference_digest(text_file, "sha256")

    def test_generate_all_hashes_binary_file(self, binary_file: Path) -> None:
        """All algorithms match references for a binary file."""
        results = generate_all_hashes(binary_file)
        assert set(results) == {"md5", "sha1", "sha256"}
        for algorithm, digest in results.items():
            assert digest == _reference_digest(binary_file, algorithm)
            assert digest == digest.lower()

    def test_empty_file_hashes(self, empty_file: Path) -> None:
        """Empty files produce valid known digests."""
        results = generate_all_hashes(empty_file)
        assert results["md5"] == hashlib.md5(b"").hexdigest()
        assert results["sha1"] == hashlib.sha1(b"").hexdigest()
        assert results["sha256"] == hashlib.sha256(b"").hexdigest()

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Missing evidence paths raise EvidenceFileError."""
        missing = tmp_path / "does-not-exist.bin"
        with pytest.raises(EvidenceFileError, match="not found"):
            generate_sha256(missing)

    def test_empty_path_raises(self) -> None:
        """Empty file paths raise EvidenceFileError."""
        with pytest.raises(EvidenceFileError, match="must not be empty"):
            generate_sha256("")

    def test_unsupported_algorithm_via_verify(self, text_file: Path) -> None:
        """Unsupported algorithms raise UnsupportedAlgorithmError."""
        with pytest.raises(UnsupportedAlgorithmError):
            verify_hash(text_file, "00", "sha512")


class TestHashVerifier:
    """Tests for hash verification."""

    def test_correct_hash(self, text_file: Path) -> None:
        """Verification succeeds when the expected digest is correct."""
        expected = generate_sha256(text_file)
        result = verify_hash(text_file, expected, "sha256")
        assert result.verified is True
        assert result.expected_hash == expected
        assert result.computed_hash == expected
        assert result.algorithm == "sha256"
        assert result.file_name == text_file.name

    def test_wrong_hash(self, text_file: Path) -> None:
        """Verification fails when the expected digest is incorrect."""
        expected = "0" * 64
        result = verify_hash(text_file, expected, "sha256")
        assert result.verified is False
        assert result.expected_hash == expected
        assert result.computed_hash != expected

    def test_tampered_hash(self, text_file: Path) -> None:
        """A single-character tamper causes verification failure."""
        genuine = generate_md5(text_file)
        tampered = ("0" if genuine[0] != "0" else "1") + genuine[1:]
        result = verify_hash(text_file, tampered, "md5")
        assert result.verified is False
        assert result.computed_hash == genuine

    def test_invalid_hash_format(self, text_file: Path) -> None:
        """Non-hex expected digests raise InvalidHashError."""
        with pytest.raises(InvalidHashError):
            verify_hash(text_file, "not-a-hex-digest", "sha1")

    def test_empty_expected_hash(self, text_file: Path) -> None:
        """Empty expected digests raise InvalidHashError."""
        with pytest.raises(InvalidHashError, match="must not be empty"):
            verify_hash(text_file, "   ", "sha1")

    def test_case_insensitive_expected_hash(self, text_file: Path) -> None:
        """Uppercase expected digests are normalized and accepted."""
        expected = generate_sha1(text_file).upper()
        result = verify_hash(text_file, expected, "SHA1")
        assert result.verified is True
        assert result.expected_hash == expected.lower()


class TestIntegrityChecker:
    """Tests for integrity checking."""

    def test_integrity_pass(self, binary_file: Path) -> None:
        """Integrity check returns PASS for the original digest."""
        original = generate_sha256(binary_file)
        result = check_integrity(binary_file, original, "sha256")
        assert result.status == IntegrityStatus.PASS
        assert result.verified is True
        assert result.original_hash == original
        assert result.computed_hash == original
        assert result.timestamp is not None

    def test_integrity_fail(self, binary_file: Path) -> None:
        """Integrity check returns FAIL for a mismatched digest."""
        result = check_integrity(binary_file, "ab" * 32, "sha256")
        assert result.status == IntegrityStatus.FAIL
        assert result.verified is False
        assert result.original_hash == "ab" * 32
        assert result.computed_hash != result.original_hash


class TestMultipleAlgorithms:
    """Cross-algorithm consistency tests."""

    @pytest.mark.parametrize("algorithm", ["md5", "sha1", "sha256"])
    def test_service_verify_each_algorithm(
        self,
        text_file: Path,
        algorithm: str,
    ) -> None:
        """HashService verifies correctly for each supported algorithm."""
        service = HashService()
        digest = generate_all_hashes(text_file)[algorithm]
        result = service.verify(text_file, digest, algorithm)
        assert result.verified is True
        assert result.algorithm == algorithm


class TestHashService:
    """Tests for HashService orchestration."""

    def test_calculate_hashes(self, text_file: Path) -> None:
        """calculate_hashes returns three HashResult models."""
        service = HashService()
        results = service.calculate_hashes(text_file)
        assert len(results) == 3
        by_algorithm = {item.algorithm: item for item in results}
        assert set(by_algorithm) == {"md5", "sha1", "sha256"}
        for algorithm, item in by_algorithm.items():
            assert item.hash == _reference_digest(text_file, algorithm)
            assert item.file_name == text_file.name
            assert item.file_size == text_file.stat().st_size

    def test_integrity_check_via_service(self, text_file: Path) -> None:
        """integrity_check wraps the checker and returns PASS."""
        service = HashService()
        digest = generate_sha256(text_file)
        result = service.integrity_check(text_file, digest, "sha256")
        assert result.status == IntegrityStatus.PASS

    def test_missing_file_via_service(self, tmp_path: Path) -> None:
        """Service methods surface EvidenceFileError for missing files."""
        service = HashService()
        with pytest.raises(EvidenceFileError):
            service.calculate_hashes(tmp_path / "missing.txt")
