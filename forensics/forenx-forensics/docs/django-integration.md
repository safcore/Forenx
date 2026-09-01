# Django / DRF Integration (Phase 10)

This repository contains two separable layers:

1. **ForenX forensic engine** (`app/`) — framework-agnostic Python package
2. **Django API host** (`backend/`) — Member 1 adapter with JWT, roles, persistence

AI assistance is advisory and does not constitute independent forensic evidence.

## Architecture

```
Frontend (Member 2)
        ↓
Django REST API + JWT (Member 1 / backend/)
        ↓
Django integration services (thin wrappers)
        ↓
ForenX services (Member 3 / app/)
        ↓
PostgreSQL or SQLite  +  evidence filesystem storage
```

## Ownership

| Responsibility | Owner |
|---|---|
| User authentication | Django |
| JWT | Django |
| Roles/permissions | Django |
| PostgreSQL / DB persistence | Django |
| Case persistence | Django |
| Evidence persistence | Django |
| File upload API | Django |
| Hash computation | ForenX |
| Metadata extraction | ForenX |
| Keyword search | ForenX |
| Browser analysis | ForenX |
| Timeline reconstruction | ForenX |
| Chain-of-custody computation | ForenX |
| Report generation | ForenX |
| AI advisory analysis | ForenX |
| Frontend UI | Member 2 |
| REST API integration | Member 1 |

## Important boundaries

- `app/` must remain importable **without Django**
- Django must **not** reimplement forensic algorithms
- Django persistence ≠ custody hash-chain computation
- AI remains local-first / advisory (`FORENX_AI_ENABLED=false` default)

## Evidence upload pipeline

```
authenticated multipart upload
  → UUID storage name (no client path trust)
  → HashService (md5/sha1/sha256)
  → MetadataService (best-effort)
  → DB transaction (Evidence row)
  → CustodyService events (uploaded + hashed)
  → JSON response
```

## Custody integration

1. Load persisted custody rows for an evidence ID
2. Rebuild an in-memory `CustodyService` ledger
3. Call `record_event(...)` / `verify_chain(...)`
4. Persist only the new/result fields

## Storage

Default root: repository `storage/` (configurable via `FORENX_STORAGE_ROOT`)

- evidence originals under `storage/evidence/`
- generated reports under `storage/reports/`

Unsafe storage names (traversal separators, empty names, null bytes, non-basename
values) are rejected with `INVALID_STORAGE_NAME`. Escape after resolution raises
`PATH_TRAVERSAL`.

API responses redact internal filesystem path fields (`absolute_path`,
`stored_path`, report output paths, etc.) via the Django integration layer.

## Configuration

| Variable | Purpose |
|----------|---------|
| `DEBUG` / `DJANGO_DEBUG` | Debug flag (`False` in production) |
| `SECRET_KEY` / `DJANGO_SECRET_KEY` | Django secret |
| `ALLOWED_HOSTS` / `DJANGO_ALLOWED_HOSTS` | Host allow-list |
| `DATABASE_URL` | Optional `postgresql://...` (else SQLite) |
| `CORS_ALLOWED_ORIGINS` | Explicit SPA origins |
| `CSRF_TRUSTED_ORIGINS` | Trusted HTTPS origins |
| `FORENX_STORAGE_ROOT` | Evidence/report storage root |
| `FORENX_MAX_UPLOAD_BYTES` | Upload size limit |
| `FORENX_AI_ENABLED` | Engine AI switch (default false) |

## Running

See `backend/README.md` for local development.

Production deployment, Gunicorn, HTTPS, PostgreSQL, static files, and backup/restore:
[PRODUCTION.md](PRODUCTION.md).

Demo / portfolio notes: [RELEASE.md](RELEASE.md).
