# ForenX Public Service API

This document describes the **implemented** public services only.

All services live under `app.services` and return Pydantic schemas from `app.schemas`.

Call `setup_logging()` once in the host process if ForenX file/console logging is required.

```python
from app.utils.logger import setup_logging
setup_logging()
```

---

## HashService

**Module:** `app.services.hash_service.HashService`

### Purpose

Compute cryptographic digests for evidence files and verify integrity.

### Public methods

| Method | Description |
|--------|-------------|
| `calculate_hashes(file_path)` | Compute MD5, SHA1, and SHA256 in one streaming pass |
| `verify(file_path, expected_hash, algorithm)` | Compare expected digest to computed digest |
| `integrity_check(file_path, original_hash, algorithm)` | Return PASS/FAIL integrity status |

### Inputs

- `file_path`: `str | pathlib.Path`
- `expected_hash` / `original_hash`: hexadecimal digest string
- `algorithm`: `"md5"`, `"sha1"`, or `"sha256"` (case-insensitive)

### Outputs

| Method | Schema |
|--------|--------|
| `calculate_hashes` | `list[HashResult]` |
| `verify` | `HashVerificationResult` |
| `integrity_check` | `IntegrityResult` |

### Example

```python
from app.services.hash_service import HashService

service = HashService()
results = service.calculate_hashes("evidence/sample_case/sample_evidence.txt")
sha256 = next(item.hash for item in results if item.algorithm == "sha256")
verification = service.verify(
    "evidence/sample_case/sample_evidence.txt",
    expected_hash=sha256,
    algorithm="sha256",
)
integrity = service.integrity_check(
    "evidence/sample_case/sample_evidence.txt",
    original_hash=sha256,
    algorithm="sha256",
)
```

---

## MetadataService

**Module:** `app.services.metadata_service.MetadataService`

### Purpose

Extract forensic metadata from images, PDFs, DOCX files, and filesystem properties.

### Public methods

| Method | Description |
|--------|-------------|
| `extract(file_path)` | Auto-detect type and extract combined metadata |
| `extract_image(file_path)` | Image / EXIF metadata |
| `extract_pdf(file_path)` | PDF document-info metadata |
| `extract_document(file_path)` | DOCX core properties |
| `extract_filesystem(file_path)` | Filesystem metadata including SHA256 |

### Inputs

- `file_path`: `str | pathlib.Path`
- Constructor may accept optional `hash_service: HashService | None`

### Outputs

| Method | Schema |
|--------|--------|
| `extract` | `MetadataResult` |
| `extract_image` | `ImageMetadata` |
| `extract_pdf` | `PdfMetadata` |
| `extract_document` | `DocumentMetadata` |
| `extract_filesystem` | `FileMetadata` |

Missing optional fields are returned as `None` (not exceptions).

### Example

```python
from app.services.metadata_service import MetadataService

service = MetadataService()
combined = service.extract("evidence/sample_case/sample_image.png")
pdf = service.extract_pdf("evidence/sample_case/sample_document.pdf")
docx = service.extract_document("evidence/sample_case/sample_document.docx")
```

---

## KeywordSearchService

**Module:** `app.services.keyword_service.KeywordSearchService`

### Purpose

Search text-like evidence, PDFs, and DOCX documents for investigator keywords.

### Public methods

| Method | Description |
|--------|-------------|
| `search(file_path, keyword, ...)` | Search one file for one keyword |
| `search_multiple(file_path, keywords, ...)` | Search one file for many keywords |
| `search_directory(directory, keywords, ...)` | Search a directory and return summary |
| `summarize_results(results)` | Aggregate per-file results |

Optional keyword flags:

- `case_sensitive` (default `False`)
- `whole_word` (default `False`)
- `regex` (default `False`)
- `context_chars` (default from config)

### Inputs

- Paths: `str | pathlib.Path`
- Keywords: `str` or sequence of strings

### Outputs

| Method | Schema |
|--------|--------|
| `search` / `search_multiple` | `KeywordResult` |
| `search_directory` | `SearchResult` (includes `KeywordSummary`) |
| `summarize_results` | `KeywordSummary` |

No matches returns empty collections / `no_matches` status (not an exception).

### Example

```python
from app.services.keyword_service import KeywordSearchService

service = KeywordSearchService()
result = service.search(
    "evidence/sample_case/sample_notes.txt",
    "confidential",
)
batch = service.search_directory(
    "evidence/sample_case",
    ["confidential", "bitcoin", "malware"],
)
```

---

## BrowserService

**Module:** `app.services.browser_service.BrowserService`

### Purpose

Analyze offline Chrome, Edge, and Firefox profile directories copied from evidence.

### Public methods

| Method | Description |
|--------|-------------|
| `analyze_browser(profile_dir, ...)` | Full profile analysis |
| `analyze_directory(directory)` | Discover and analyze profiles under a tree |
| `extract_history(profile_dir)` | History visits only |
| `extract_downloads(profile_dir)` | Downloads only |
| `extract_bookmarks(profile_dir)` | Bookmarks only |
| `extract_cookies(profile_dir)` | Cookie metadata only (never values) |
| `extract_searches(profile_dir)` | Detected search queries |
| `extract_login_pages(profile_dir)` | Likely login/auth pages |
| `summarize(results)` | Aggregate one or many profile results |
| `detect_browser(profile_dir)` | Return detected browser label |

### Inputs

- `profile_dir` / `directory`: `str | pathlib.Path`
- Optional `browser` override and `profile_name`

### Outputs

| Method | Schema |
|--------|--------|
| `analyze_browser` | `BrowserResult` |
| `analyze_directory` | `list[BrowserResult]` |
| `extract_history` | `list[BrowserVisit]` |
| `extract_downloads` | `list[BrowserDownload]` |
| `extract_bookmarks` | `list[BrowserBookmark]` |
| `extract_cookies` | `list[BrowserCookieMetadata]` |
| `extract_searches` | `list[BrowserSearch]` |
| `extract_login_pages` | `list[BrowserLoginPage]` |
| `summarize` | `BrowserSummary` |
| `detect_browser` | `str` |

### Example

```python
from app.services.browser_service import BrowserService

service = BrowserService()
result = service.analyze_browser(
    "evidence/sample_case/browser/chrome/Default"
)
print(result.browser, result.summary.history_count, result.summary.search_count)
```

---

## TimelineService

**Module:** `app.services.timeline_service.TimelineService`

### Purpose

Reconstruct a forensic timeline from filesystem timestamps, browser artifacts, and embedded metadata dates. Reuses `BrowserService` and `MetadataService` (does not re-parse browser databases).

### Public methods

| Method | Description |
|--------|-------------|
| `build_timeline(evidence_path, ...)` | Build from a file, browser profile, or directory |
| `build_from_file(file_path, ...)` | Single-file timeline (filesystem + metadata) |
| `build_from_directory(directory, ...)` | Directory timeline with optional browser discovery |
| `filter_by_time_range(events, start_time=, end_time=)` | Inclusive time-range filter (non-mutating) |
| `filter_by_event_type(events, event_types)` | Filter by controlled event types |
| `filter_events(events, timeline_filter)` | Combined filter (`TimelineFilter`) |
| `sort_events(events)` | Chronological + deterministic secondary sort |
| `summarize(events_or_result)` | Aggregate counts and earliest/latest |

### Inputs

- `evidence_path` / `file_path` / `directory`: `str | pathlib.Path`
- Flags: `include_filesystem`, `include_browser`, `include_metadata` (booleans)
- Filters: `datetime` bounds, `TimelineEventType` values, source labels

### Outputs

| Method | Schema |
|--------|--------|
| `build_timeline` / `build_from_file` / `build_from_directory` | `TimelineResult` |
| Filter / sort helpers | `list[TimelineEvent]` |
| `summarize` | `TimelineSummary` |

### Example

```python
from app.services.timeline_service import TimelineService
from app.schemas.timeline import TimelineEventType, TimelineFilter

service = TimelineService()
result = service.build_timeline("evidence/sample_case")
print(result.summary.total_events, result.summary.earliest_event, result.summary.latest_event)

visits = service.filter_by_event_type(
    result.events,
    [TimelineEventType.BROWSER_VISIT],
)
```

---

## CustodyService

**Module:** `app.services.custody_service.CustodyService`

### Purpose

Record append-only, tamper-evident chain-of-custody events and verify evidence SHA-256 bindings. Persistence and authentication belong to the Django backend.

### Public methods

| Method | Description |
|--------|-------------|
| `build_event(...)` | Build a hashed custody event without appending |
| `record_event(...)` | Build and append an event to the in-memory ledger |
| `get_chain(evidence_id=None)` | Return custody events |
| `get_ledger_snapshot(evidence_id=None)` | Serializable ledger snapshot |
| `get_latest_event(evidence_id=None)` | Latest event helper |
| `verify_chain(evidence_id=None)` | Verify hash-chain integrity |
| `verify_evidence_integrity(file_path, expected_sha256, ...)` | File vs custody SHA-256 |
| `export_for_timeline(evidence_id=None)` | Host-consumable timestamp export |

### Inputs

- Required: `evidence_id`, `action`, `description`
- Optional actor / source metadata: `actor_id`, `actor_role`, `source`, `source_ip`
- Optional integrity binding: `evidence_sha256` (64-hex SHA-256)
- Optional provenance: `evidence_path`, `original_filename`, `file_size`, `metadata`

### Outputs

| Method | Schema |
|--------|--------|
| `build_event` / `record_event` / `get_latest_event` | `CustodyEvent` |
| `get_chain` | `list[CustodyEvent]` |
| `get_ledger_snapshot` | `CustodyLedger` |
| `verify_chain` | `CustodyVerificationResult` |
| `verify_evidence_integrity` | `EvidenceIntegrityResult` |

### Example

```python
from app.services.custody_service import CustodyService
from app.schemas.custody import CustodyAction

service = CustodyService()
service.record_event(
    evidence_id="EV-001",
    action=CustodyAction.EVIDENCE_ACQUIRED,
    description="Seized workstation image",
    actor_id="inv-1",
    actor_role="investigator",
    source_ip="203.0.113.10",
    evidence_sha256="a" * 64,
)
print(service.verify_chain("EV-001").valid)
```

Integration contract: [custody-integration.md](custody-integration.md)

---

## ReportService

**Module:** `app.services.report_service.ReportService`

### Purpose

Aggregate already-computed Phase 2–7 forensic results into a derived investigation report and export JSON / PDF artifacts under `outputs/reports/`.

### Public methods

| Method | Description |
|--------|-------------|
| `build_report(...)` | Aggregate inputs into `ForensicReport` |
| `validate_report(report)` | Validate identity/status/findings constraints |
| `generate_json(report, ...)` | Write deterministic UTF-8 JSON |
| `generate_pdf(report, ...)` | Write ReportLab PDF |
| `generate_report(report, output_format=...)` | Convenience JSON/PDF dispatcher |
| `dumps_json(report)` | Deterministic JSON text without writing |

### Outputs

| Method | Schema / type |
|--------|----------------|
| `build_report` | `ForensicReport` |
| generate_* | `ReportGenerationResult` |

### Example

```python
from app.services.report_service import ReportService

service = ReportService()
report = service.build_report(
    case_id="CASE-1",
    evidence_id="EV-1",
    hash_results=hashes,
    integrity=integrity,
    keyword=keyword_result,
    browser=browser_result,
    timeline=timeline_result,
    custody_events=events,
    custody_verification=verification,
)
service.generate_report(report, output_format="pdf")
```

Integration notes: [report-integration.md](report-integration.md)

---

## AIService

**Module:** `app.services.ai_service.AIService`

### Purpose

Produce optional, advisory AI-assisted investigation output from already-computed
forensic results. Default configuration keeps AI disabled and offline-compatible.

### Public methods

| Method | Description |
|--------|-------------|
| `analyze(...)` | Full assistive analysis over supplied forensic artifacts |
| `summarize_case(...)` | Analyst-oriented narrative summary |
| `explain_findings(...)` | Explain deterministic findings |
| `generate_investigation_questions(...)` | Follow-up investigation questions |
| `prioritize_findings(...)` | Priority ordering using assistive heuristics |
| `build_context(...)` | Build sanitized `AIContextSummary` only |

### Configuration

| Setting | Default | Meaning |
|---------|---------|---------|
| `FORENX_AI_ENABLED` | `false` | Master switch |
| `FORENX_AI_PROVIDER` | `local` | Provider selector |
| `FORENX_AI_MODEL` | `deterministic-local` | Model label |
| `FORENX_AI_ALLOW_NETWORK` | `false` | Gate for future remote clients |

### Outputs

| Method | Schema |
|--------|--------|
| analyze / helpers | `AIAnalysis` |

### Example

```python
from app.services.ai_service import AIService

analysis = AIService(enabled=True, provider_name="local").analyze(
    case_id="CASE-1",
    evidence_id="EV-1",
    hash_results=hashes,
    integrity=integrity,
    keyword=keyword_result,
    timeline=timeline_result,
    custody_verification=verification,
)
# Attach optionally:
report = ReportService().build_report(
    case_id="CASE-1",
    evidence_id="EV-1",
    hash_results=hashes,
    ai_analysis=analysis,
)
```

Integration notes: [ai-integration.md](ai-integration.md)

---

## Django REST API (Phase 10 host)

The Django adapter under `backend/` exposes JWT-protected routes that call the
services above. Engine APIs are unchanged.

| Method | Path | Service / purpose |
|--------|------|-------------------|
| POST | `/api/auth/register/` | registration |
| POST | `/api/auth/login/` | JWT login |
| GET | `/api/auth/me/` | current user |
| GET/POST | `/api/cases/` | case list/create |
| GET/POST | `/api/cases/<id>/evidence/` | evidence list/upload |
| POST | `/api/evidence/<id>/hash/` | `HashService` |
| GET | `/api/evidence/<id>/metadata/` | read-only stored metadata result |
| POST | `/api/evidence/<id>/metadata/analyze/` | `MetadataService` |
| POST | `/api/evidence/<id>/keywords/` | `KeywordSearchService` |
| GET | `/api/evidence/<id>/browser/` | read-only stored browser result |
| POST | `/api/evidence/<id>/browser/analyze/` | `BrowserService` |
| GET | `/api/evidence/<id>/timeline/` | read-only stored timeline result |
| POST | `/api/evidence/<id>/timeline/analyze/` | `TimelineService` |
| GET | `/api/evidence/<id>/custody/` | custody list |
| GET | `/api/evidence/<id>/custody/verify/` | `CustodyService.verify_chain` |
| POST | `/api/evidence/<id>/report/` | `ReportService` |
| POST | `/api/evidence/<id>/ai/` | `AIService` |
| GET | `/api/reports/<id>/download/` | authenticated download |

Full host documentation: [django-integration.md](django-integration.md)

---

## Error model

Domain failures raise subclasses of `ForenXError` from `app.utils.exceptions`.

Typical examples:

- `EvidenceFileError` — missing / inaccessible path
- `UnsupportedFileTypeError` — unsupported extension
- `UnsupportedAlgorithmError` — unknown hash algorithm
- `InvalidHashError` — malformed digest
- `KeywordSearchError` — invalid regex / unreadable document
- `BrowserHistoryError` — corrupted / unrecognized browser DB
- `MetadataExtractionError` — unreadable image/PDF/DOCX payload
- `TimelineError` — invalid timestamp / timeline filter / reconstruction failure
- `CustodyError` — invalid custody event / broken append / chain rules
- `ReportError` / `ReportGenerationError` — invalid report data / output path / format
- `AIAnalysisError` — invalid AI request / context construction failure

Absence of matches or missing optional metadata fields is **not** an error.
Corrupt individual artifacts in a directory may produce warnings without aborting the whole run.
