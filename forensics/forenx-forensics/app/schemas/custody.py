"""Pydantic schemas for chain-of-custody and evidence audit trails.

The hash-chained ledger is **append-only** and **tamper-evident**. It is not
physically immutable; persistence controls belong to the Django backend.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CustodyAction(str, Enum):
    """Controlled custody actions for evidence lifecycle events.

    New actions may be added without removing existing values.
    """

    EVIDENCE_ACQUIRED = "evidence_acquired"
    EVIDENCE_REGISTERED = "evidence_registered"
    EVIDENCE_UPLOADED = "evidence_uploaded"
    EVIDENCE_HASHED = "evidence_hashed"
    EVIDENCE_VERIFIED = "evidence_verified"
    EVIDENCE_ACCESSED = "evidence_accessed"
    EVIDENCE_EXAMINED = "evidence_examined"
    EVIDENCE_ANALYZED = "evidence_analyzed"
    EVIDENCE_EXPORTED = "evidence_exported"
    EVIDENCE_TRANSFERRED = "evidence_transferred"
    EVIDENCE_CLOSED = "evidence_closed"
    AI_ANALYSIS_PERFORMED = "ai_analysis_performed"


class CustodyStatus(str, Enum):
    """High-level status for custody operations and ledger snapshots."""

    SUCCESS = "success"
    PARTIAL = "partial"
    EMPTY = "empty"
    ERROR = "error"
    VALID = "valid"
    INVALID = "invalid"


class EvidenceIntegrityStatus(str, Enum):
    """Outcome of binding a custody SHA-256 to a current evidence file."""

    VERIFIED = "verified"
    MISMATCH = "mismatch"
    MISSING = "missing"
    ERROR = "error"


class CustodyEvent(BaseModel):
    """Normalized append-only custody / audit-trail event."""

    event_id: str
    evidence_id: str
    action: CustodyAction
    timestamp: datetime
    actor_id: str | None = None
    actor_role: str | None = None
    source: str | None = None
    source_ip: str | None = None
    description: str
    evidence_sha256: str | None = None
    previous_event_hash: str | None = None
    event_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_path: str | None = None
    original_filename: str | None = None
    file_size: int | None = Field(default=None, ge=0)


class CustodyLedger(BaseModel):
    """Serializable snapshot of an append-only custody chain.

    This is a Pydantic view for APIs / persistence mapping. The runtime
    in-memory ledger lives in ``app.custody.ledger.CustodyLedger``.
    """

    evidence_id: str | None = None
    events: list[CustodyEvent] = Field(default_factory=list)
    event_count: int = Field(ge=0, default=0)
    latest_event_hash: str | None = None
    status: CustodyStatus = CustodyStatus.EMPTY
    message: str = ""


class CustodyVerificationResult(BaseModel):
    """Structured result of verifying a custody hash chain."""

    valid: bool
    event_count: int = Field(ge=0, default=0)
    first_event: CustodyEvent | None = None
    last_event: CustodyEvent | None = None
    broken_event_id: str | None = None
    message: str
    warnings: list[str] = Field(default_factory=list)
    status: CustodyStatus = CustodyStatus.EMPTY


class EvidenceIntegrityResult(BaseModel):
    """Result of comparing a custody-recorded SHA-256 to a file on disk."""

    evidence_id: str | None = None
    file_path: str | None = None
    expected_sha256: str | None = None
    computed_sha256: str | None = None
    status: EvidenceIntegrityStatus
    verified: bool
    message: str
    timestamp: datetime
