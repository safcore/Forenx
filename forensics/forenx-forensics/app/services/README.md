# ForenX Services Layer

This package will host **reusable forensic business logic** for the ForenX engine.

Services are intentionally separate from:

- `app/` feature modules (low-level operations)
- `app/models/` (domain data structures)
- `app/schemas/` (validation / serialization contracts)
- Django views / API layers (future)

## Purpose

The services layer orchestrates forensic workflows and exposes stable interfaces that can be called from:

- `main.py` / CLI entry points
- unit and integration tests
- a future Django backend

## Planned Services

| Service | Responsibility | Status |
|---------|----------------|--------|
| `HashService` | Evidence hashing and hash verification | Implemented (Phase 2) |
| `MetadataService` | Image / document metadata extraction | Implemented (Phase 3) |
| `KeywordSearchService` | Keyword / pattern search across evidence | Implemented (Phase 4) |
| `BrowserService` | Browser history and artifact analysis | Implemented (Phase 5) |
| `TimelineService` | Event correlation and timeline reconstruction | Implemented (Phase 6) |
| `CustodyService` | Chain of custody and evidence audit trail | Implemented (Phase 7) |
| `ReportService` | Investigation report assembly and export | Implemented (Phase 8) |
| `AIService` | AI-assisted investigation (advisory, local-first) | Implemented (Phase 9) |
