# ForenX – AI-Assisted Digital Forensics Investigation Platform

Standalone Python forensic engine designed for clean integration into a Django backend (Member 1) and React frontend (Member 2).

**Version:** 1.0.0  
**License:** MIT  
**Status:** Phases 1–10 complete

---

## Project Overview

ForenX Forensics is a framework-agnostic Python package that performs digital forensics analysis on local evidence files. It exposes a service layer (`HashService`, `MetadataService`, `KeywordSearchService`, `BrowserService`, `TimelineService`, `CustodyService`, `ReportService`, `AIService`) that returns validated Pydantic schemas. Host applications (Django, CLI, notebooks) import these services; the engine never imports Django.

---

## Features

- Streaming MD5 / SHA1 / SHA256 hashing with verify and integrity checks
- Image, PDF, DOCX, and filesystem metadata extraction
- Keyword search across text, PDF, and DOCX (file, multi-keyword, directory)
- Offline Chrome / Edge / Firefox browser artifact analysis
- Timeline reconstruction from filesystem, browser, and metadata timestamps
- Chain of custody / evidence audit trail with tamper-evident hash chaining
- Forensic JSON / PDF report generation from existing service results
- Optional AI-assisted investigation (local-first, advisory, offline by default)
- Centralized config, logging, and domain exception hierarchy
- Sample evidence and a demo entry point for local validation

---

## Architecture

```
React Frontend
      ↓
Django Backend
      ↓
Forensics Engine (this repository)
      ↓
Evidence Files
```

| Layer | Responsibility |
|-------|----------------|
| Frontend | Case UI and presentation (Member 2; out of repo) |
| Backend | API, auth, persistence, orchestration (Member 1; out of repo) |
| Forensics Engine | Hashing, metadata, keyword, browser, timeline, custody, reports, advisory AI |
| Evidence Files | Read-only forensic input; never modified by the engine |

Full details: [docs/architecture.md](docs/architecture.md)

---

## Folder Structure

```
forenx-forensics/
├── app/                   # Member 3 forensic engine (Django-free)
├── backend/               # Member 1 Django/DRF integration host (Phase 10)
├── docs/
├── tests/                 # Engine pytest suite
├── evidence/
├── storage/               # Runtime evidence/report storage (gitignored)
├── outputs/
├── main.py                # Engine demo only (not Django)
├── requirements.txt
├── requirements-django.txt
└── ...
```

---

## Installation

Requirements: **Python 3.12+**

```powershell
cd forenx-forensics
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Editable install (recommended when hosting from Django):

```powershell
pip install -e .
# or with test tools:
pip install -e ".[dev]"
```

---

## Requirements

See [requirements.txt](requirements.txt). Runtime dependencies include Pydantic, Pillow, pypdf, and python-docx. Pytest is listed for local development.

Package metadata (name, version, license, authors, Python version) lives in [pyproject.toml](pyproject.toml). Version is read from [VERSION](VERSION) (`1.0.0`).

---

## Running

```powershell
python main.py
```

Demo walks Phases 2–9 via public services only. Call `setup_logging()` once from your host process before production use.

---

## Testing

```powershell
pytest
pytest tests/test_hashing.py -q
```

See [docs/testing.md](docs/testing.md).

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/architecture.md](docs/architecture.md) | System layers and `app/` packages |
| [docs/api.md](docs/api.md) | Public service API |
| [docs/integration.md](docs/integration.md) | Django / Member 1 integration |
| [docs/developer-guide.md](docs/developer-guide.md) | Standards and module workflow |
| [docs/phases.md](docs/phases.md) | Phase status |
| [docs/testing.md](docs/testing.md) | Env, pytest, demos |
| [docs/custody-integration.md](docs/custody-integration.md) | Member 1 custody / PostgreSQL contract |
| [docs/report-integration.md](docs/report-integration.md) | Member 1/2 report integration contract |
| [docs/ai-integration.md](docs/ai-integration.md) | Phase 9 AI provider / Django AI contract |
| [docs/django-integration.md](docs/django-integration.md) | Phase 10 Django/DRF host adapter |
| [backend/README.md](backend/README.md) | Backend runbook |
| [CHANGELOG.md](CHANGELOG.md) | Version / phase history |

---

## Integration

```python
from app.services.hash_service import HashService
from app.services.metadata_service import MetadataService
from app.services.keyword_service import KeywordSearchService
from app.services.browser_service import BrowserService
from app.services.timeline_service import TimelineService
from app.services.custody_service import CustodyService
from app.services.report_service import ReportService
from app.services.ai_service import AIService

hashes = HashService().calculate_hashes("evidence/sample_case/sample_evidence.txt")
meta = MetadataService().extract("evidence/sample_case/sample_image.png")
hits = KeywordSearchService().search("evidence/sample_case/sample_notes.txt", "confidential")
browser = BrowserService().analyze_browser("evidence/sample_case/browser/chrome/Default")
timeline = TimelineService().build_timeline("evidence/sample_case")
custody = CustodyService()
reports = ReportService()
ai = AIService()  # disabled by default; pass enabled=True for local fallback
```

| Service | Methods |
|---------|---------|
| `HashService` | `calculate_hashes()`, `verify()`, `integrity_check()` |
| `MetadataService` | `extract()`, `extract_image()`, `extract_pdf()`, `extract_document()`, `extract_filesystem()` |
| `KeywordSearchService` | `search()`, `search_multiple()`, `search_directory()`, `summarize_results()` |
| `BrowserService` | `analyze_browser()`, `analyze_directory()`, `extract_*()`, `summarize()` |
| `TimelineService` | `build_timeline()`, `build_from_file()`, `build_from_directory()`, `filter_*()`, `sort_events()`, `summarize()` |
| `CustodyService` | `record_event()`, `build_event()`, `get_chain()`, `verify_chain()`, `verify_evidence_integrity()` |
| `ReportService` | `build_report()`, `generate_json()`, `generate_pdf()`, `generate_report()`, `validate_report()` |
| `AIService` | `analyze()`, `summarize_case()`, `explain_findings()`, `generate_investigation_questions()`, `prioritize_findings()` |

The forensic engine must remain independent from Django. Sample wrappers and install notes: [docs/integration.md](docs/integration.md).

---

## Current Status

| Phase | Capability | Status |
|-------|------------|--------|
| 1 | Project architecture | Complete |
| 2 | Evidence hashing | Complete |
| 3 | Metadata extraction | Complete |
| 4 | Keyword search | Complete |
| 5 | Browser analysis | Complete |
| 6 | Timeline reconstruction | Complete |
| 7 | Chain of custody | Complete |
| 8 | Report generation | Complete |
| 9 | AI-assisted investigation | Complete |
| 10 | Django / DRF integration | Complete |

---

## Roadmap

1. Frontend (Member 2) consumes `backend/` JWT APIs
2. Future Phase 11+ capabilities (not in this repository yet)

---

## Contributors

| Role | Focus |
|------|--------|
| Member 1 | Django backend / JWT / PostgreSQL / DRF API (`backend/`) |
| Member 2 | React frontend (API consumer; out of repo) |
| Member 3 | Forensics engine (`app/`; this package core) |

---

## License

MIT License. See [LICENSE](LICENSE).
