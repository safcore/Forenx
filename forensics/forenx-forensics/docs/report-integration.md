# Forensic Report Integration (Member 1 / Member 2)

Phase 8 exposes `ReportService` for derived JSON/PDF investigation reports.

## Architecture

```
Existing forensic services (Phases 2–7)
        ↓
ReportService.build_report(...)
        ↓
ForensicReport schema
        ↓
JSON / PDF renderers
        ↓
outputs/reports/
        ↓
Django persists metadata + storage reference (Member 1)
        ↓
React downloads / displays reports (Member 2)
```

The engine does **not** implement Django models, views, URLs, or REST endpoints.

## Engine API

```python
from app.services.report_service import ReportService

service = ReportService()
report = service.build_report(
    case_id="CASE-1",
    evidence_id="EV-1",
    hash_results=hashes,
    integrity=integrity,
    metadata=metadata,
    keyword=search_result,
    browser=browser_result,
    timeline=timeline_result,
    custody_events=custody_events,
    custody_verification=custody_verification,
)
json_out = service.generate_json(report)
pdf_out = service.generate_pdf(report)
```

## Django Persistence Recommendations

Persist report metadata only in Django / PostgreSQL:

- report_id
- case_id
- evidence_id
- status
- generated_at
- generated_by
- json_path / pdf_path (or object-storage keys)
- sha256 of evidence at generation time

Do not reimplement aggregation logic in Django.

## Security

- Reports never include cookie values, passwords, or tokens
- Evidence files are never modified
- Invalid custody chains are reported as invalid (status PARTIAL), never silently SUCCESS

## Outputs

Default directory: `outputs/reports/`

Filenames:

`forenx_report_<case_id>_<evidence_id>.json|.pdf`
