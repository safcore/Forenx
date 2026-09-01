"""Build validated custody events with hash-chain linkage."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.custody.models import (
    compute_event_hash_for_event,
    ensure_utc_aware,
    event_hash_from_fields,
    make_event_id,
)
from app.hashing.hash_verifier import normalize_hash_digest
from app.schemas.custody import CustodyAction, CustodyEvent
from app.utils.exceptions import CustodyError, InvalidHashError
from app.utils.logger import get_logger

logger = get_logger(__name__)

_SHA256_HEX_LENGTH = 64


def _normalize_optional_text(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _normalize_sha256(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    try:
        normalized = normalize_hash_digest(value)
    except InvalidHashError as exc:
        raise CustodyError(f"Invalid evidence_sha256: {exc}") from exc
    if len(normalized) != _SHA256_HEX_LENGTH:
        raise CustodyError(
            "Invalid evidence_sha256: SHA-256 digests must be 64 hexadecimal characters"
        )
    return normalized


def _coerce_action(action: CustodyAction | str) -> CustodyAction:
    if isinstance(action, CustodyAction):
        return action
    try:
        return CustodyAction(str(action).strip().lower())
    except ValueError as exc:
        raise CustodyError(f"Unsupported custody action: {action!r}") from exc


def build_custody_event(
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
) -> CustodyEvent:
    """Construct a custody event with a deterministic ``event_hash``.

    Events are only created when this builder is explicitly called. Actor fields
    may be omitted; authentication remains a host (Django) responsibility.

    Raises:
        CustodyError: If required fields are missing or invalid.
    """
    evidence_key = _normalize_optional_text(evidence_id, field_name="evidence_id")
    if not evidence_key:
        raise CustodyError("evidence_id is required for custody events")

    if action is None or (isinstance(action, str) and not action.strip()):
        raise CustodyError("action is required for custody events")

    description_text = description if description is not None else ""
    if not str(description_text).strip():
        raise CustodyError("description is required for custody events")

    if file_size is not None and file_size < 0:
        raise CustodyError("file_size must be >= 0 when provided")

    action_value = _coerce_action(action)
    try:
        event_time = ensure_utc_aware(timestamp or datetime.now(timezone.utc))
    except ValueError as exc:
        raise CustodyError(str(exc)) from exc

    actor = _normalize_optional_text(actor_id, field_name="actor_id")
    role = _normalize_optional_text(actor_role, field_name="actor_role")
    source_value = _normalize_optional_text(source, field_name="source")
    ip_value = _normalize_optional_text(source_ip, field_name="source_ip")
    sha256 = _normalize_sha256(evidence_sha256)
    previous = _normalize_optional_text(
        previous_event_hash, field_name="previous_event_hash"
    )
    if previous is not None:
        try:
            previous = normalize_hash_digest(previous)
        except InvalidHashError as exc:
            raise CustodyError(f"Invalid previous_event_hash: {exc}") from exc
        if len(previous) != _SHA256_HEX_LENGTH:
            raise CustodyError(
                "Invalid previous_event_hash: must be a 64-character SHA-256 digest"
            )

    meta = dict(metadata or {})
    resolved_event_id = (
        _normalize_optional_text(event_id, field_name="event_id")
        or make_event_id(
            evidence_id=evidence_key,
            action=action_value,
            timestamp=event_time,
            actor_id=actor,
            description=str(description_text).strip(),
        )
    )

    event_hash = event_hash_from_fields(
        event_id=resolved_event_id,
        evidence_id=evidence_key,
        action=action_value,
        timestamp=event_time,
        actor_id=actor,
        actor_role=role,
        source=source_value,
        source_ip=ip_value,
        description=str(description_text).strip(),
        evidence_sha256=sha256,
        previous_event_hash=previous,
        metadata=meta,
        evidence_path=_normalize_optional_text(evidence_path, field_name="evidence_path"),
        original_filename=_normalize_optional_text(
            original_filename, field_name="original_filename"
        ),
        file_size=file_size,
    )

    event = CustodyEvent(
        event_id=resolved_event_id,
        evidence_id=evidence_key,
        action=action_value,
        timestamp=event_time,
        actor_id=actor,
        actor_role=role,
        source=source_value,
        source_ip=ip_value,
        description=str(description_text).strip(),
        evidence_sha256=sha256,
        previous_event_hash=previous,
        event_hash=event_hash,
        metadata=meta,
        evidence_path=_normalize_optional_text(evidence_path, field_name="evidence_path"),
        original_filename=_normalize_optional_text(
            original_filename, field_name="original_filename"
        ),
        file_size=file_size,
    )

    # Defensive self-check that the stored hash matches canonicalization.
    recomputed = compute_event_hash_for_event(event)
    if recomputed != event.event_hash:
        raise CustodyError("Internal error: custody event hash mismatch during build")

    logger.info(
        "Built custody event id=%s evidence_id=%s action=%s",
        event.event_id,
        event.evidence_id,
        event.action.value,
    )
    return event
