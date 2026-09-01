# Chain of Custody Integration Contract (Member 1)

This document defines how the Django backend should integrate with the ForenX
`CustodyService`. The forensic engine remains framework-independent.

## Architecture Boundary

```
React
  ↓
Django REST API (+ JWT auth)
  ↓
Django / PostgreSQL persistence
  ↓
ForenX CustodyService (this package)
```

Do **not** import Django, DRF, JWT libraries, or PostgreSQL drivers into this
engine repository.

## Runtime Flow

```
Django receives request
        ↓
JWT identifies authenticated user
        ↓
Django determines:
  actor_id
  actor_role
  source_ip
  evidence_id
        ↓
Django calls CustodyService.record_event(...)
        ↓
Custody event generated (hash-chained, append-only)
        ↓
Django persists CustodyEvent fields in PostgreSQL
```

## Engine API

```python
from app.services.custody_service import CustodyService
from app.schemas.custody import CustodyAction

service = CustodyService()

event = service.record_event(
    evidence_id="EV-123",
    action=CustodyAction.EVIDENCE_EXAMINED,
    description="Opened evidence package for review",
    actor_id=str(request.user.id),
    actor_role=request.user.role,  # host-supplied metadata
    source="django",
    source_ip=request.META.get("REMOTE_ADDR"),
    evidence_sha256=evidence.sha256,  # prefer existing stored SHA-256
    evidence_path=str(evidence.storage_path),
    original_filename=evidence.original_filename,
    file_size=evidence.file_size,
    metadata={"case_id": str(case.id)},
)

verification = service.verify_chain("EV-123")
integrity = service.verify_evidence_integrity(
    evidence.storage_path,
    evidence.sha256,
    evidence_id="EV-123",
)
```

Important:

- Do not verify JWTs inside the engine.
- Do not discover client IP inside the engine.
- Do not silently recalculate SHA-256 when recording unless the host explicitly
  hashes via `HashService` first and passes the digest.

## Append-Only Semantics

`CustodyService` / `CustodyLedger` do **not** support:

- `update_event()`
- `delete_event()`

If a prior record was incorrect, append a **corrective** event.

The hash chain is **tamper-evident** and **integrity-verifiable**. It is **not**
physically immutable. Database immutability is a future backend hardening task.

## Recommended Django Model Shape

Do **not** create this model in the engine repo. Suggested Conceptual model:

```python
class EvidenceCustodyEvent(models.Model):
    evidence = models.ForeignKey("Evidence", on_delete=models.PROTECT, related_name="custody_events")

    event_id = models.CharField(max_length=64, unique=True)
    action = models.CharField(max_length=64)
    timestamp = models.DateTimeField()
    actor_id = models.CharField(max_length=128, null=True, blank=True)
    actor_role = models.CharField(max_length=64, null=True, blank=True)
    source = models.CharField(max_length=64, null=True, blank=True)
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    description = models.TextField()
    evidence_sha256 = models.CharField(max_length=64, null=True, blank=True)
    previous_event_hash = models.CharField(max_length=64, null=True, blank=True)
    event_hash = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp", "id"]
```

Recommended constraints:

- unique `event_id`
- index on `(evidence_id, timestamp)`
- store exact `event_hash` / `previous_event_hash` produced by ForenX

PostgreSQL is **not** immutable by default. Treat engine verification as the
tamper-evidence check when loading historical events back into `CustodyService`
or `verify_custody_chain()`.

## Persistence Strategy

1. Call `CustodyService.record_event(...)` to obtain a validated event.
2. Persist `event.model_dump(mode="json")` fields into PostgreSQL.
3. To verify later:
   - load ordered events for one evidence ID
   - reconstruct `CustodyEvent` models
   - call `verify_custody_chain(events)` or rebuild an in-memory ledger and
     `verify_chain(evidence_id)`

## Recommended Backend Role Policy

Enforced by Django (not by the engine):

| Role | Suggested permissions |
|------|------------------------|
| Administrator | All custody actions |
| Lead Investigator | Most investigative actions |
| Investigator | access / examine / analyze |
| Analyst | analyze / examine |
| Auditor | read / verify / export audit records |

## Canonical Hash Notes

`event_hash` is SHA-256 over deterministic JSON (`sort_keys=True`, compact
separators, UTF-8, UTC timestamps with `Z`). See `app/custody/models.py`.

## Timeline Boundary

Custody events can later be consumed by timeline views via
`CustodyService.export_for_timeline()`.

Do **not** make `TimelineService` import `CustodyService` in a way that creates
cycles. Prefer host-level orchestration in Django.
