"""Tamper-evident verification for custody hash chains."""

from __future__ import annotations

from collections.abc import Sequence

from app.custody.models import compute_event_hash_for_event
from app.schemas.custody import (
    CustodyEvent,
    CustodyStatus,
    CustodyVerificationResult,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def verify_custody_chain(
    events: Sequence[CustodyEvent],
) -> CustodyVerificationResult:
    """Verify ordering, hashes, and previous-hash links for a custody chain.

    Args:
        events: Ordered custody events for a single evidence_id (preferred) or
            a pre-filtered sequence.

    Returns:
        Structured ``CustodyVerificationResult`` (never a bare boolean).
    """
    items = list(events)
    warnings: list[str] = []

    if not items:
        result = CustodyVerificationResult(
            valid=True,
            event_count=0,
            first_event=None,
            last_event=None,
            broken_event_id=None,
            message="Custody chain is empty",
            warnings=warnings,
            status=CustodyStatus.EMPTY,
        )
        logger.info("Custody chain verification: empty chain considered valid")
        return result

    seen_ids: set[str] = set()
    evidence_ids = {item.evidence_id for item in items}
    if len(evidence_ids) > 1:
        warnings.append(
            "Verification received events from multiple evidence_id values; "
            "verify each evidence chain separately for strongest guarantees"
        )

    for index, event in enumerate(items):
        if event.event_id in seen_ids:
            message = f"Duplicate event_id detected: {event.event_id}"
            logger.warning("Custody verification failed: %s", message)
            return CustodyVerificationResult(
                valid=False,
                event_count=len(items),
                first_event=items[0],
                last_event=items[-1],
                broken_event_id=event.event_id,
                message=message,
                warnings=warnings,
                status=CustodyStatus.INVALID,
            )
        seen_ids.add(event.event_id)

        expected_hash = compute_event_hash_for_event(event)
        if event.event_hash != expected_hash:
            message = (
                f"event_hash mismatch at event_id={event.event_id} "
                "(payload may have been tampered with)"
            )
            logger.warning("Custody verification failed: %s", message)
            return CustodyVerificationResult(
                valid=False,
                event_count=len(items),
                first_event=items[0],
                last_event=items[-1],
                broken_event_id=event.event_id,
                message=message,
                warnings=warnings,
                status=CustodyStatus.INVALID,
            )

        if index == 0:
            if event.previous_event_hash is not None:
                message = (
                    f"First event must have previous_event_hash=None "
                    f"(event_id={event.event_id})"
                )
                logger.warning("Custody verification failed: %s", message)
                return CustodyVerificationResult(
                    valid=False,
                    event_count=len(items),
                    first_event=items[0],
                    last_event=items[-1],
                    broken_event_id=event.event_id,
                    message=message,
                    warnings=warnings,
                    status=CustodyStatus.INVALID,
                )
        else:
            previous = items[index - 1]
            if event.previous_event_hash != previous.event_hash:
                message = (
                    f"Broken previous_event_hash link at event_id={event.event_id}"
                )
                logger.warning("Custody verification failed: %s", message)
                return CustodyVerificationResult(
                    valid=False,
                    event_count=len(items),
                    first_event=items[0],
                    last_event=items[-1],
                    broken_event_id=event.event_id,
                    message=message,
                    warnings=warnings,
                    status=CustodyStatus.INVALID,
                )

            if event.timestamp < previous.timestamp:
                warnings.append(
                    f"Event timestamps are not non-decreasing around "
                    f"event_id={event.event_id}"
                )

    result = CustodyVerificationResult(
        valid=True,
        event_count=len(items),
        first_event=items[0],
        last_event=items[-1],
        broken_event_id=None,
        message="Custody chain verification succeeded",
        warnings=warnings,
        status=CustodyStatus.VALID,
    )
    logger.info(
        "Custody chain verification succeeded events=%d",
        result.event_count,
    )
    return result
