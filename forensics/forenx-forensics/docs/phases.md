# ForenX Development Phases

## Completed Phases

### Phase 1 — Project Architecture

Scaffolded the standalone Python package, configuration, logging, models, exception hierarchy, placeholder feature packages, and demo entry point.

### Phase 2 — Evidence Hashing

Implemented streaming MD5 / SHA1 / SHA256 generation, verification, integrity checking, hash schemas, and `HashService`.

### Phase 3 — Metadata Extraction

Implemented image, PDF, DOCX, and filesystem metadata extractors, metadata schemas, and `MetadataService` with typed dispatch.

### Phase 4 — Keyword Search

Implemented text / PDF / DOCX keyword search with directory scan, summaries, keyword schemas, and `KeywordSearchService`.

### Phase 5 — Browser Analysis

Implemented offline Chrome / Edge / Firefox profile analysis (history, downloads, bookmarks, cookie metadata, searches, login pages), browser schemas, and `BrowserService`.

### Phase 6 — Timeline Reconstruction — COMPLETE

Implemented timeline extraction, normalization, sorting, filtering, and `TimelineService`.

### Phase 7 — Chain of Custody — COMPLETE

Implemented append-only, tamper-evident custody ledger events and `CustodyService`.

### Phase 8 — Forensic Report Generation — COMPLETE

Implemented deterministic forensic report aggregation and export:

- aggregates Phase 2–7 service outputs without re-running analyzers by default
- produces structured `ForensicReport` schemas
- exports deterministic UTF-8 JSON
- exports multi-section PDF via ReportLab
- writes derived artifacts under `outputs/reports/`
- preserves provenance and limitations
- reports invalid custody chains as invalid (never silent SUCCESS)
- redacts secret-like fields (`cookie_value`, passwords, tokens)
- remains Django-independent

See [report-integration.md](report-integration.md) and [api.md](api.md).

### Phase 9 — AI-Assisted Investigation — COMPLETE

Implemented an optional, local-first assistive analysis layer above deterministic services:

- provider abstraction with offline deterministic fallback
- sanitized / bounded forensic context builder
- deterministic prompt builder
- `AIService` orchestration returning structured `AIAnalysis`
- optional AI report section clearly labeled as advisory
- no external AI network calls required for core functionality or tests
- AI assistance does not modify evidence, hashes, or custody ledgers

See [ai-integration.md](ai-integration.md) and [api.md](api.md).

### Phase 10 — Django / DRF Integration — COMPLETE

Implemented a separated Django host adapter under `backend/`:

- JWT auth + role model (Administrator / Lead / Investigator / Analyst / Auditor)
- Case / Evidence / AnalysisRun / CustodyEventRecord / ReportRecord persistence
- Thin DRF wrappers calling existing ForenX services (no algorithm duplication)
- Secure evidence upload pipeline with hashing + custody events
- Report download + AI advisory endpoints
- SQLite default; PostgreSQL via `DATABASE_URL`
- Integration tests under `backend/tests/`

See [django-integration.md](django-integration.md) and [backend/README.md](../backend/README.md).

### Phases 11–16 — Investigation product APIs — COMPLETE

Controlled timeline, metadata, report, AI, dashboard, reports, custody, analysis history, global evidence inventory, and live analytics. Forensic engines were not rewritten.

### Phase 17 — Production hardening — COMPLETE

Environment-variable configuration, secret handling, CORS/CSRF, JWT, upload limits, and sanitized production errors.

### Phase 17.2 — Explicit analysis POST — COMPLETE

Browser, timeline, and metadata analysis run on `POST /api/evidence/<id>/{browser,timeline,metadata}/analyze/`. Matching GET routes are read-only.

### Phase 18 — PostgreSQL, static files, Gunicorn — COMPLETE

`DATABASE_URL` selects PostgreSQL while SQLite remains the local/test default. `STATIC_URL` / `STATIC_ROOT`, `collectstatic`, and Gunicorn are configured. `runserver` is not used in production.

### Phase 19 — Backup and recovery — COMPLETE

Documented in [PRODUCTION.md](PRODUCTION.md): daily PostgreSQL dumps, persistent evidence/report storage, restore procedure, and immutability of original acquired evidence.

### Phase 20 — Final QA — COMPLETE

Backend tests, frontend production build, and Django `--deploy` checks. No Phase 21.

See [RELEASE.md](RELEASE.md) for demo and presentation notes.

---

## Current Package Version

`1.0.0` (see root `VERSION`)
