"""Dispatch helpers for custody recording and integrity checks."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from app.custody.ledger import CustodyLedger
from app.custody.verifier import verify_custody_chain
from app.hashing.hash_generator import resolve_evidence_path
from app.hashing.hash_verifier import normalize_hash_digest
from app.hashing.integrity_checker import check_integrity
from app.schemas.custody import (
    CustodyEvent,
    CustodyLedger as CustodyLedgerSnapshot,
    CustodyStatus,
    CustodyVerificationResult,
    EvidenceIntegrityResult,
    EvidenceIntegrityStatus,
)
from app.utils.exceptions import EvidenceFileError, InvalidHashError
from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.services.hash_service import HashService

logger = get_logger(__name__)


def snapshot_ledger(
    ledger: CustodyLedger,
    evidence_id: str | None = None,
) -> CustodyLedgerSnapshot:
    """Build a serializable ledger snapshot for a chain."""
    events = ledger.get_events(evidence_id)
    latest = events[-1].event_hash if events else None
    if not events:
        status = CustodyStatus.EMPTY
        message = "No custody events recorded"
    else:
        status = CustodyStatus.SUCCESS
        message = f"Custody ledger contains {len(events)} event(s)"
    return CustodyLedgerSnapshot(
        evidence_id=evidence_id,
        events=events,
        event_count=len(events),
        latest_event_hash=latest,
        status=status,
        message=message,
    )


def verify_ledger_chain(
    ledger: CustodyLedger,
    evidence_id: str | None = None,
) -> CustodyVerificationResult:
    """Verify one evidence chain, or all chains when ``evidence_id`` is omitted."""
    if evidence_id is not None:
        return verify_custody_chain(ledger.get_events(evidence_id))

    all_events = ledger.get_events()
    if not all_events:
        return verify_custody_chain([])

    warnings: list[str] = []
    for key in sorted({event.evidence_id for event in all_events}):
        result = verify_custody_chain(ledger.get_events(key))
        warnings.extend(result.warnings)
        if not result.valid:
            return CustodyVerificationResult(
                valid=False,
                event_count=len(all_events),
                first_event=result.first_event,
                last_event=result.last_event,
                broken_event_id=result.broken_event_id,
                message=result.message,
                warnings=warnings,
                status=CustodyStatus.INVALID,
            )

    ordered = all_events
    return CustodyVerificationResult(
        valid=True,
        event_count=len(ordered),
        first_event=ordered[0],
        last_event=ordered[-1],
        broken_event_id=None,
        message="All custody chains verified successfully",
        warnings=warnings,
        status=CustodyStatus.VALID,
    )


def verify_evidence_sha256(
    *,
    file_path: str | Path,
    expected_sha256: str,
    evidence_id: str | None = None,
    hash_service: HashService | None = None,
) -> EvidenceIntegrityResult:
    """Verify an evidence file against a custody-recorded SHA-256 digest.

    Reuses Phase 2 hashing utilities / optional ``HashService``. Does not modify
    the evidence file.
    """
    now = datetime.now(timezone.utc)
    path_text = str(file_path) if file_path is not None else None

    try:
        normalized = normalize_hash_digest(expected_sha256)
    except InvalidHashError as exc:
        return EvidenceIntegrityResult(
            evidence_id=evidence_id,
            file_path=path_text,
            expected_sha256=None,
            computed_sha256=None,
            status=EvidenceIntegrityStatus.ERROR,
            verified=False,
            message=f"Invalid expected SHA-256: {exc}",
            timestamp=now,
        )

    if len(normalized) != 64:
        return EvidenceIntegrityResult(
            evidence_id=evidence_id,
            file_path=path_text,
            expected_sha256=normalized,
            computed_sha256=None,
            status=EvidenceIntegrityStatus.ERROR,
            verified=False,
            message="Expected SHA-256 must be 64 hexadecimal characters",
            timestamp=now,
        )

    try:
        path = resolve_evidence_path(file_path)
    except EvidenceFileError as exc:
        logger.warning("Evidence integrity check missing file: %s", exc)
        return EvidenceIntegrityResult(
            evidence_id=evidence_id,
            file_path=path_text,
            expected_sha256=normalized,
            computed_sha256=None,
            status=EvidenceIntegrityStatus.MISSING,
            verified=False,
            message=str(exc),
            timestamp=now,
        )

    try:
        if hash_service is not None:
            integrity = hash_service.integrity_check(
                path,
                original_hash=normalized,
                algorithm="sha256",
            )
            verified = integrity.verified
            computed = integrity.computed_hash
        else:
            integrity = check_integrity(
                path,
                original_hash=normalized,
                algorithm="sha256",
            )
            verified = integrity.verified
            computed = integrity.computed_hash
    except (EvidenceFileError, InvalidHashError) as exc:
        return EvidenceIntegrityResult(
            evidence_id=evidence_id,
            file_path=str(path),
            expected_sha256=normalized,
            computed_sha256=None,
            status=EvidenceIntegrityStatus.ERROR,
            verified=False,
            message=str(exc),
            timestamp=now,
        )

    if verified:
        status = EvidenceIntegrityStatus.VERIFIED
        message = "Evidence SHA-256 matches custody-recorded digest"
    else:
        status = EvidenceIntegrityStatus.MISMATCH
        message = "Evidence SHA-256 does not match custody-recorded digest"

    logger.info(
        "Evidence integrity check path=%s status=%s",
        path.name,
        status.value,
    )
    return EvidenceIntegrityResult(
        evidence_id=evidence_id,
        file_path=str(path),
        expected_sha256=normalized,
        computed_sha256=computed,
        status=status,
        verified=verified,
        message=message,
        timestamp=now,
    )


def export_events_for_timeline(events: list[CustodyEvent]) -> list[dict]:
    """Export minimal timestamped dictionaries for future timeline consumers.

    Does not import or call ``TimelineService`` (avoids circular dependencies).
    """
    exported: list[dict] = []
    for event in events:
        exported.append(
            {
                "timestamp": event.timestamp,
                "event_type": f"custody.{event.action.value}",
                "source": "custody",
                "source_file": event.evidence_path,
                "description": event.description,
                "evidence_id": event.evidence_id,
                "event_id": event.event_id,
                "metadata": {
                    "actor_id": event.actor_id,
                    "actor_role": event.actor_role,
                    "evidence_sha256": event.evidence_sha256,
                    "event_hash": event.event_hash,
                },
            }
        )
    return exported
