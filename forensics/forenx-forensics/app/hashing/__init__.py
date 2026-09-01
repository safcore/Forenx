"""Evidence hashing and integrity package.

Public helpers:

- ``generate_md5``, ``generate_sha1``, ``generate_sha256``, ``generate_all_hashes``
- ``verify_hash``
- ``check_integrity``
"""

from app.hashing.hash_generator import (
    SUPPORTED_HASH_ALGORITHMS,
    generate_all_hashes,
    generate_md5,
    generate_sha1,
    generate_sha256,
)
from app.hashing.hash_verifier import verify_hash
from app.hashing.integrity_checker import check_integrity

__all__ = [
    "SUPPORTED_HASH_ALGORITHMS",
    "generate_md5",
    "generate_sha1",
    "generate_sha256",
    "generate_all_hashes",
    "verify_hash",
    "check_integrity",
]
