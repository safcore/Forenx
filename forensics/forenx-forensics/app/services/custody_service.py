"""Chain-of-custody service orchestration for the ForenX forensics engine.

Provides the public Phase 7 API for append-only, tamper-evident custody
event recording and verification. Persistence belongs to Member 1 (Django).

Typical usage example:

    from app.services.custody_service import CustodyService
    from app.schemas.custody import CustodyAction

    service = CustodyService()
    service.record_event(
        evidence_id="EV-001",
        action=CustodyAction.EVIDENCE_ACQUIRED,
        description="Seized workstation disk image",
        actor_id="analyst-1",
        actor_role="investigator",
        evidence_sha256="a" * 64,
    )
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from app.custody.dispatcher import (
    export_events_for_timeline,
    snapshot_ledger,
    verify_evidence_sha256,
    verify_ledger_chain,
)
from app.custody.event_builder import build_custody_event
from app.custody.ledger import CustodyLedger
from app.schemas.custody import (
    CustodyAction,
    CustodyEvent,
    CustodyLedger as CustodyLedgerSnapshot,
    CustodyVerificationResult,
    EvidenceIntegrityResult,
)
from app.services.hash_service import HashService
from app.utils.exceptions import CustodyError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CustodyService:
    """High-level API for chain-of-custody recording and verification.

    Designed for reuse by CLI tools, tests, and a future Django backend.
    The engine does not authenticate actors or persist to PostgreSQL.
    """

    def __init__(
        self,
        *,
        ledger: CustodyLedger | None = None,
        hash_service: HashService | None = None,
    ) -> None:
        """Initialize the custody service.

        Args:
            ledger: Optional shared in-memory ledger (tests / process scope).
            hash_service: Optional Phase 2 ``HashService`` for integrity checks.
        """
        self._ledger = ledger or CustodyLedger()
        self._hash_service = hash_service or HashService()

    @property
    def ledger(self) -> CustodyLedger:
        """Return the underlying in-memory ledger instance."""
        return self._ledger

    def build_event(
        self,
        *,
        evidence_id: str,
        action: CustodyAction | str,
        description: str,
        actor_id: str | None = None,
        actor_role: str | None = None,
        source: str | None = None,
        source_ip: str | None = None,
        evidence_sha256: str | None = None,
        previous_event_hash: str | None = None,
        metadata: dict[str, Any] | None = None,
        evidence_path: str | None = None,
        original_filename: str | None = None,
        file_size: int | None = None,
        timestamp: datetime | None = None,
        event_id: str | None = None,
        link_to_latest: bool = False,
    ) -> CustodyEvent:
        """Build a custody event without appending it.

        When ``link_to_latest`` is true, ``previous_event_hash`` is taken from
        the latest ledger event for ``evidence_id`` (unless the chain is empty).
        """
        previous = previous_event_hash
        if link_to_latest:
            latest = self._ledger.get_latest(evidence_id)
            previous = latest.event_hash if latest else None

        return build_custody_event(
            evidence_id=evidence_id,
            action=action,
            description=description,
            actor_id=actor_id,
            actor_role=actor_role,
            source=source,
            source_ip=source_ip,
            evidence_sha256=evidence_sha256,
            previous_event_hash=previous,
            metadata=metadata,
            evidence_path=evidence_path,
            original_filename=original_filename,
            file_size=file_size,
            timestamp=timestamp,
            event_id=event_id,
        )

    def record_event(
        self,
        *,
        evidence_id: str,
        action: CustodyAction | str,
        description: str,
        actor_id: str | None = None,
        actor_role: str | None = None,
        source: str | None = None,
        source_ip: str | None = None,
        evidence_sha256: str | None = None,
        metadata: dict[str, Any] | None = None,
        evidence_path: str | None = None,
        original_filename: str | None = None,
        file_size: int | None = None,
        timestamp: datetime | None = None,
        event_id: str | None = None,
    ) -> CustodyEvent:
        """Build and append a custody event to the ledger (append-only)."""
        logger.info(
            "CustodyService.record_event started evidence_id=%s action=%s",
            evidence_id,
            action,
        )
        event = self._ledger.append_action(
            evidence_id=evidence_id,
            action=action,
            description=description,
            actor_id=actor_id,
            actor_role=actor_role,
            source=source,
            source_ip=source_ip,
            evidence_sha256=evidence_sha256,
            metadata=metadata,
            evidence_path=evidence_path,
            original_filename=original_filename,
            file_size=file_size,
            timestamp=timestamp,
            event_id=event_id,
        )
        logger.info(
            "CustodyService.record_event finished event_id=%s hash=%s...",
            event.event_id,
            event.event_hash[:12],
        )
        return event

    def get_chain(self, evidence_id: str | None = None) -> list[CustodyEvent]:
        """Return custody events for one evidence_id or the entire ledger."""
        return self._ledger.get_events(evidence_id)

    def get_ledger_snapshot(
        self, evidence_id: str | None = None
    ) -> CustodyLedgerSnapshot:
        """Return a serializable ledger snapshot for API / persistence mapping."""
        return snapshot_ledger(self._ledger, evidence_id)

    def get_latest_event(self, evidence_id: str | None = None) -> CustodyEvent | None:
        """Return the latest custody event for an evidence item or overall."""
        return self._ledger.get_latest(evidence_id)

    def verify_chain(
        self, evidence_id: str | None = None
    ) -> CustodyVerificationResult:
        """Verify hash-chain integrity for one or all evidence chains."""
        logger.info(
            "CustodyService.verify_chain started evidence_id=%s",
            evidence_id,
        )
        result = verify_ledger_chain(self._ledger, evidence_id)
        logger.info(
            "CustodyService.verify_chain finished valid=%s events=%d",
            result.valid,
            result.event_count,
        )
        return result

    def verify_evidence_integrity(
        self,
        file_path: str | Path,
        expected_sha256: str,
        *,
        evidence_id: str | None = None,
    ) -> EvidenceIntegrityResult:
        """Verify that an evidence file still matches a custody SHA-256."""
        logger.info(
            "CustodyService.verify_evidence_integrity started path=%s",
            Path(file_path).name if file_path else "",
        )
        result = verify_evidence_sha256(
            file_path=file_path,
            expected_sha256=expected_sha256,
            evidence_id=evidence_id,
            hash_service=self._hash_service,
        )
        logger.info(
            "CustodyService.verify_evidence_integrity finished status=%s",
            result.status.value,
        )
        return result

    def export_for_timeline(
        self, evidence_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Export custody timestamps for optional timeline consumption.

        Does not call ``TimelineService``.
        """
        return export_events_for_timeline(self.get_chain(evidence_id))

    def assert_append_only(self) -> None:
        """Document append-only semantics for hosts / tests."""
        raise CustodyError(
            "Custody ledgers are append-only. Incorrect history must be corrected "
            "by appending a new event; updates and deletes are not supported."
        )