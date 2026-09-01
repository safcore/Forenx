# ForenX System Architecture

## Overall Architecture

ForenX is delivered as a three-member system. This repository is Member 3: the standalone Python forensics engine.

```
React Frontend  (Member 2)
        │
        │  HTTPS / JSON
        ▼
Django Backend  (Member 1)
        │
        │  Python imports
        ▼
Forensics Engine  (Member 3 / this repository)
        │
        │  read-only analysis
        ▼
Evidence Files  (disk / uploaded case storage)
```

The backend orchestrates cases, users, and APIs. The engine performs forensic analysis. The frontend presents investigation workflows to analysts.

---

## Responsibilities

### Frontend (React)

- Case UI and investigator workflows
- Uploading / selecting evidence
- Displaying hashes, metadata, keyword hits, browser artifacts, timelines, and custody/audit records
- Never embeds forensic algorithms

### Backend (Django)

- Authentication and authorization
- Case / evidence persistence
- REST API endpoints
- Calls ForenX services and maps schema results to API responses
- Must not fork or embed engine source inside Django apps unless packaged

### Forensics Engine (this repository)

- Cryptographic hashing and integrity checks
- Metadata extraction
- Keyword search
- Offline browser artifact analysis
- Framework-independent schemas and services
- Never imports Django or React

### Evidence Files

- Original digital evidence retained on disk
- Engine copies SQLite browser DBs to temp locations before querying
- Original evidence is never modified by the engine

---

## Internal Engine Layers

| Layer | Package | Role |
|-------|---------|------|
| Entry / demo | `main.py` | Demonstration only |
| Services | `app/services/` | Public orchestration API |
| Feature modules | `app/hashing/`, `app/metadata/`, `app/keyword/`, `app/browser/`, `app/timeline/`, `app/custody/`, `app/reports/`, `app/ai/` | Algorithms / custody / reporting / assistive AI |
| Schemas | `app/schemas/` | Pydantic contracts |
| Models | `app/models/` | Framework-agnostic domain types |
| Utils | `app/utils/` | Config, logging, exceptions |
| Placeholders | _(none for Phases 1–9)_ | Reserved packages consumed through Phase 9 |
| Tests | `tests/` | Pytest suite |
| Evidence / outputs | `evidence/`, `outputs/` | Sample inputs and analysis output dirs |

---

## Package Guide (`app/`)

### `app/hashing/`

Streaming MD5 / SHA1 / SHA256 generation, verification, and integrity checking.

### `app/metadata/`

Image, PDF, DOCX, and filesystem metadata extraction with typed dispatch.

### `app/keyword/`

Text / PDF / DOCX keyword search, directory search, and match summarization.

### `app/browser/`

Chrome, Edge, and Firefox offline profile analysis (history, downloads, bookmarks, cookie metadata, searches, login pages).

### `app/timeline/`

Timeline reconstruction: filesystem / browser / metadata extractors, timestamp normalization, dispatch, sorting, filtering soft correlation.

### `app/custody/`

Append-only, tamper-evident chain-of-custody ledger, event builder, verifier, and dispatch helpers.

### `app/reports/`

Report aggregation, deterministic JSON export, and ReportLab PDF rendering for derived investigation reports.

### `app/ai/`

Optional AI-assisted investigation: context builder, prompt builder, provider abstraction, and deterministic local fallback (no network required).

### `app/services/`

Public service classes intended for import by Django and demos:

- `HashService`
- `MetadataService`
- `KeywordSearchService`
- `BrowserService`
- `TimelineService`
- `CustodyService`
- `ReportService`
- `AIService`

### `app/schemas/`

Pydantic models returned by services (`HashResult`, `MetadataResult`, `KeywordResult`, `BrowserResult`, `TimelineResult`, `CustodyEvent`, `ForensicReport`, `AIAnalysis`, etc.).

### `app/models/`

Lightweight domain dataclasses (for example `Evidence`).

### `app/utils/`

Shared `config`, rotating logger, and custom exception hierarchy.

---

## Design Principles

1. Clean architecture with unidirectional dependency flow toward services.
2. Services return Pydantic schemas only.
3. Feature packages stay usable without Django.
4. Logging is lazy (`setup_logging()` at host startup).
5. Evidence integrity: original files are treated as read-only.
6. AI assistance is advisory only and cannot mutate forensic facts.

---

## Django Host Adapter (`backend/`)

Phase 10 adds an optional Django/DRF project under `backend/` that adapts ForenX
services for Member 1 (auth, persistence, API) without importing Django into
`app/`.

Ownership table and setup: [django-integration.md](django-integration.md).
