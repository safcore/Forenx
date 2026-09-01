"""Chain-of-custody package (Phase 7).

Provides append-only, tamper-evident custody event recording with SHA-256
hash chaining. Persistence and authentication belong to the host application.
"""

from app.custody.event_builder import build_custody_event
from app.custody.ledger import CustodyLedger
from app.custody.verifier import verify_custody_chain

__all__ = [
    "CustodyLedger",
    "build_custody_event",
    "verify_custody_chain",
]
