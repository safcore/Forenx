"""Phase 7 chain-of-custody implementation notes.

Historical placeholder retained for package completeness. Prefer importing
from ``app.services.custody_service.CustodyService``.

Semantics:
- append-only event history
- tamper-evident SHA-256 hash chaining
- no Django / PostgreSQL persistence in this package
"""
