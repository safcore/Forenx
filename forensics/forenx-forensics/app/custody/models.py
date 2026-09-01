"""Internal helpers and canonicalization for custody hash chaining.

Canonical event hashing rules
-----------------------------
``event_hash`` is ``SHA-256`` over a UTF-8 JSON payload with:

- stable sorted object keys (``sort_keys=True``)
- compact separators (``,`` and ``:``; no insignificant whitespace)
- ``ensure_ascii=False`` so Unicode is stable and explicit
- timestamps as UTC ISO-8601 with ``Z`` suffix (``...T12:00:00Z``)
- ``null`` for missing optional values
- nested ``metadata`` also sorted recursively

Fields included in the hash input:

``event_id``, ``evidence_id``, ``action``, ``timestamp``, ``actor_id``,
``actor_role``, ``source``, ``source_ip``, ``description``,
``evidence_sha256``, ``previous_event_hash``, ``metadata``,
``evidence_path``, ``original_filename``, ``file_size``

``event_hash`` itself is never included in the hashed payload.

The chain is append-only and tamper-evident — not physically immutable.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.schemas.custody import CustodyAction, CustodyEvent

# Stable namespace for deterministic event IDs when callers do not supply one.
CUSTODY_EVENT_NAMESPACE = uuid.UUID("a9c3e7f1-2b84-4d6a-9e05-71c8d4f0b2a6")


def ensure_utc_aware(value: datetime) -> datetime:
    """Require / normalize a timezone-aware UTC datetime.

    Args:
        value: Timestamp supplied by the caller.

    Returns:
        UTC-aware datetime.

    Raises:
        ValueError: If ``value`` is not a ``datetime``.
    """
    if not isinstance(value, datetime):
        raise ValueError(f"timestamp must be datetime, got {type(value).__name__}")
    if value.tzinfo is None:
        # Custody records reject silent local-clock ambiguity.
        raise ValueError(
            "Custody timestamps must be timezone-aware; naive values are rejected"
        )
    return value.astimezone(timezone.utc)


def datetime_to_canonical(value: datetime) -> str:
    """Serialize a datetime to a stable UTC ISO-8601 string ending in ``Z``."""
    utc_value = ensure_utc_aware(value)
    text = utc_value.replace(microsecond=utc_value.microsecond).isoformat()
    # Prefer trailing Z over +00:00 for stable hashing.
    if text.endswith("+00:00"):
        text = text[:-6] + "Z"
    return text


def _canonicalize_value(value: Any) -> Any:
    """Recursively convert values into JSON-serializable canonical forms."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return datetime_to_canonical(value)
    if isinstance(value, CustodyAction):
        return value.value
    if isinstance(value, dict):
        return {str(key): _canonicalize_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonicalize_value(item) for item in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        return value
    return str(value)


def build_canonical_payload(
    *,
    event_id: str,
    evidence_id: str,
    action: CustodyAction | str,
    timestamp: datetime,
    actor_id: str | None,
    actor_role: str | None,
    source: str | None,
    source_ip: str | None,
    description: str,
    evidence_sha256: str | None,
    previous_event_hash: str | None,
    metadata: dict[str, Any] | None,
    evidence_path: str | None = None,
    original_filename: str | None = None,
    file_size: int | None = None,
) -> dict[str, Any]:
    """Build the deterministic dictionary used for ``event_hash``."""
    action_value = action.value if isinstance(action, CustodyAction) else str(action)
    return {
        "action": action_value,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "description": description,
        "event_id": event_id,
        "evidence_id": evidence_id,
        "evidence_path": evidence_path,
        "evidence_sha256": evidence_sha256,
        "file_size": file_size,
        "metadata": _canonicalize_value(metadata or {}),
        "original_filename": original_filename,
        "previous_event_hash": previous_event_hash,
        "source": source,
        "source_ip": source_ip,
        "timestamp": datetime_to_canonical(timestamp),
    }


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    """Serialize a payload to deterministic UTF-8 JSON bytes."""
    return json.dumps(
        _canonicalize_value(payload),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def compute_event_hash(payload: dict[str, Any]) -> str:
    """Compute SHA-256 hex digest for a canonical event payload."""
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def event_hash_from_fields(
    *,
    event_id: str,
    evidence_id: str,
    action: CustodyAction | str,
    timestamp: datetime,
    actor_id: str | None,
    actor_role: str | None,
    source: str | None,
    source_ip: str | None,
    description: str,
    evidence_sha256: str | None,
    previous_event_hash: str | None,
    metadata: dict[str, Any] | None,
    evidence_path: str | None = None,
    original_filename: str | None = None,
    file_size: int | None = None,
) -> str:
    """Compute ``event_hash`` from event fields (excluding ``event_hash``)."""
    payload = build_canonical_payload(
        event_id=event_id,
        evidence_id=evidence_id,
        action=action,
        timestamp=timestamp,
        actor_id=actor_id,
        actor_role=actor_role,
        source=source,
        source_ip=source_ip,
        description=description,
        evidence_sha256=evidence_sha256,
        previous_event_hash=previous_event_hash,
        metadata=metadata,
        evidence_path=evidence_path,
        original_filename=original_filename,
        file_size=file_size,
    )
    return compute_event_hash(payload)


def compute_event_hash_for_event(event: CustodyEvent) -> str:
    """Recompute the expected hash for an existing ``CustodyEvent``."""
    return event_hash_from_fields(
        event_id=event.event_id,
        evidence_id=event.evidence_id,
        action=event.action,
        timestamp=event.timestamp,
        actor_id=event.actor_id,
        actor_role=event.actor_role,
        source=event.source,
        source_ip=event.source_ip,
        description=event.description,
        evidence_sha256=event.evidence_sha256,
        previous_event_hash=event.previous_event_hash,
        metadata=event.metadata,
        evidence_path=event.evidence_path,
        original_filename=event.original_filename,
        file_size=event.file_size,
    )


def make_event_id(
    *,
    evidence_id: str,
    action: CustodyAction | str,
    timestamp: datetime,
    actor_id: str | None,
    description: str,
) -> str:
    """Build a deterministic UUID5 event identifier."""
    action_value = action.value if isinstance(action, CustodyAction) else str(action)
    payload = "|".join(
        [
            evidence_id,
            action_value,
            datetime_to_canonical(timestamp),
            actor_id or "",
            description,
        ]
    )
    return str(uuid.uuid5(CUSTODY_EVENT_NAMESPACE, payload))
