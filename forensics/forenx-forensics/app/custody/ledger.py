"""In-memory append-only custody ledger.

This ledger is framework-independent and process-local. PostgreSQL persistence
belongs to the Django backend (Member 1). The hash chain is tamper-evident,
not physically immutable.
"""

from __future__ import annotations

from app.custody.event_builder import build_custody_event
from app.custody.models import compute_event_hash_for_event
from app.schemas.custody import CustodyAction, CustodyEvent
from app.utils.exceptions import CustodyError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CustodyLedger:
    """Append-only in-memory custody ledger keyed by ``evidence_id``.

    There is intentionally no ``update_event`` or ``delete_event``. Incorrect
    historical records should be corrected by appending a new event.
    """

    def __init__(self) -> None:
        self._chains: dict[str, list[CustodyEvent]] = {}
        self._event_ids: set[str] = set()

    def append(self, event: CustodyEvent) -> CustodyEvent:
        """Append a fully built custody event to its evidence chain.

        Raises:
            CustodyError: On duplicate IDs or broken previous-hash linkage.
        """
        if event.event_id in self._event_ids:
            raise CustodyError(f"Duplicate custody event_id: {event.event_id}")

        chain = self._chains.setdefault(event.evidence_id, [])
        if not chain:
            if event.previous_event_hash is not None:
                raise CustodyError(
                    "First custody event for an evidence_id must have "
                    "previous_event_hash=None"
                )
        else:
            latest = chain[-1]
            if event.previous_event_hash != latest.event_hash:
                raise CustodyError(
                    "previous_event_hash does not match the latest event hash "
                    f"for evidence_id={event.evidence_id}"
                )

        expected_hash = compute_event_hash_for_event(event)
        if event.event_hash != expected_hash:
            raise CustodyError(
                f"event_hash is invalid for event_id={event.event_id}"
            )

        stored = event.model_copy(deep=True)
        chain.append(stored)
        self._event_ids.add(stored.event_id)
        logger.info(
            "Appended custody event id=%s evidence_id=%s action=%s chain_len=%d",
            stored.event_id,
            stored.evidence_id,
            stored.action.value,
            len(chain),
        )
        return stored.model_copy(deep=True)

    def append_action(
        self,
        *,
        evidence_id: str,
        action: CustodyAction | str,
        description: str,
        **kwargs,
    ) -> CustodyEvent:
        """Build and append an event linked to the current tip of the chain."""
        previous = None
        chain = self._chains.get(evidence_id, [])
        if chain:
            previous = chain[-1].event_hash
        event = build_custody_event(
            evidence_id=evidence_id,
            action=action,
            description=description,
            previous_event_hash=previous,
            **kwargs,
        )
        return self.append(event)

    def get_events(self, evidence_id: str | None = None) -> list[CustodyEvent]:
        """Return a deep-copied list of events (optionally for one evidence_id)."""
        if evidence_id is None:
            events: list[CustodyEvent] = []
            for key in sorted(self._chains):
                events.extend(item.model_copy(deep=True) for item in self._chains[key])
            return events
        return [
            item.model_copy(deep=True) for item in self._chains.get(evidence_id, [])
        ]

    def get_latest(self, evidence_id: str | None = None) -> CustodyEvent | None:
        """Return the latest event for an evidence_id, or globally by timestamp."""
        if evidence_id is not None:
            chain = self._chains.get(evidence_id, [])
            if not chain:
                return None
            return chain[-1].model_copy(deep=True)

        latest: CustodyEvent | None = None
        for chain in self._chains.values():
            if not chain:
                continue
            candidate = chain[-1]
            if latest is None or candidate.timestamp >= latest.timestamp:
                latest = candidate
        return latest.model_copy(deep=True) if latest else None

    def clear(self) -> None:
        """Clear all events.

        Intended for isolated unit tests only. Production hosts should not use
        this to rewrite history; append a corrective event instead.
        """
        self._chains.clear()
        self._event_ids.clear()
        logger.info("Custody ledger cleared")
