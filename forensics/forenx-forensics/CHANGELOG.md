# Changelog

All notable project milestones for the ForenX forensics engine are documented in this file.

The format is intentionally phase-oriented for academic tracking.

## [1.0.0] — Phase 1 to Phase 5 baseline

### Phase 1 — Project Architecture

- Created package scaffold and clean directory layout
- Added centralized config, logging, and exception hierarchy
- Added domain `Evidence` model and placeholder feature packages
- Added README, LICENSE, VERSION, pyproject packaging baseline

### Phase 2 — Evidence Hashing

- Added streaming MD5 / SHA1 / SHA256 hashing
- Added hash verification and integrity PASS/FAIL checks
- Added hash Pydantic schemas
- Added `HashService`
- Added hashing tests and sample text evidence

### Phase 3 — Metadata Extraction

- Added image, PDF, DOCX, and filesystem metadata extractors
- Added metadata schemas and typed dispatch
- Added `MetadataService`
- Added metadata tests and sample image/PDF/DOCX evidence
- Added Pillow, pypdf, and python-docx dependencies

### Phase 4 — Keyword Search

- Added text/PDF/DOCX keyword search with context snippets
- Added directory search and keyword frequency summaries
- Added keyword schemas
- Added `KeywordSearchService`
- Added keyword tests and forensic keyword sample files

### Phase 5 — Browser Analysis

- Added offline Chrome / Edge / Firefox profile analysis
- Added history, downloads, bookmarks, cookie metadata, searches, login pages
- Added browser schemas and forensic-safe SQLite copy/read workflow
- Added `BrowserService`
- Added browser tests and synthetic browser profile samples

### Documentation / Packaging (Pre-Phase 6 Preparation)

- Added `docs/` architecture, API, integration, developer, phases, and testing guides
- Expanded README and created CHANGELOG
- Confirmed packaging metadata consistency for version `1.0.0`

## [1.0.0] — Phase 6 Timeline Reconstruction

### Phase 6 — Timeline Reconstruction

- Added normalized timeline event model and Pydantic schemas
- Added filesystem / browser / metadata timeline extractors
- Added timestamp normalizer with documented naive-UTC policy
- Added dispatcher, soft correlation hints, sorting, and filtering
- Added `TimelineService` public API
- Added Phase 6 tests and sample timeline note under `evidence/sample_case/timeline/`
- Extended `main.py` demo for timeline reconstruction
- Updated docs (`phases.md`, `api.md`, README)

## [1.0.0] — Phase 7 Chain of Custody

### Phase 7 — Chain of Custody

- Added custody schemas (`CustodyEvent`, verification / integrity results)
- Added append-only in-memory ledger with SHA-256 hash chaining
- Added deterministic canonical serialization and tamper verification
- Added `CustodyService` public API and evidence integrity binding via `HashService`
- Added Phase 7 tests and Member 1 integration contract (`docs/custody-integration.md`)
- Extended `main.py` demo for chain-of-custody recording / verification

## [1.0.0] — Phase 8 Forensic Report Generation

### Phase 8 — Forensic Report Generation

- Added report schemas (`ForensicReport`, section models, findings, notes)
- Added report aggregator / builder / JSON + PDF renderers (ReportLab)
- Added `ReportService` public API writing to `outputs/reports/`
- Added secret redaction and path-traversal protection
- Added Phase 8 tests and `docs/report-integration.md`
- Extended `main.py` demo for JSON/PDF report generation
- Added `reportlab` dependency

## [1.0.0] — Phase 9 AI-Assisted Investigation

### Phase 9 — AI-Assisted Investigation & Evidence Interpretation

- Added AI schemas distinguishing observed facts, inferences, and recommendations
- Added local-first provider abstraction with deterministic offline fallback
- Added sanitized/bounded context builder and deterministic prompt builder
- Added `AIService` public API (`analyze`, summarize, explain, questions, prioritize)
- Extended optional AI section on forensic reports (JSON/PDF)
- Added Phase 9 tests (`tests/test_ai.py`) and synthetic sample under `evidence/sample_case/ai/`
- Added `docs/ai-integration.md` and updated architecture/API/integration docs
- Configuration: `FORENX_AI_ENABLED=false` by default; no network/API keys required

## [1.0.0] — Phase 10 Django / DRF Integration

### Phase 10 — Django / DRF Integration

- Added separated `backend/` Django project (accounts + investigations apps)
- JWT authentication (SimpleJWT) and role-based permissions
- Case / Evidence / AnalysisRun / CustodyEvent / Report persistence models
- Evidence upload pipeline calling `HashService`, `MetadataService`, `CustodyService`
- Analysis endpoints wrapping all Phase 2–9 ForenX services
- Secure UUID evidence storage under `storage/`
- Integration tests (`backend/tests/`) and `docs/django-integration.md`
- Core `app/` remains Django-free

## Unreleased

### Phase 11+

Not Implemented Yet
