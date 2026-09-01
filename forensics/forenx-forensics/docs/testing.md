# Testing Guide

## Creating a Virtual Environment

### Windows (PowerShell)

```powershell
cd forenx-forensics
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
cd forenx-forensics
python3 -m venv .venv
source .venv/bin/activate
```

---

## Installing Requirements

```bash
pip install -r requirements.txt
```

Optional editable install:

```bash
pip install -e ".[dev]"
```

---

## Running All Tests

```bash
pytest
```

Quiet mode:

```bash
pytest -q
```

Expected result (engine only, Phases 1–9):

```text
183 passed
```

Django integration (Phase 10), from `backend/`:

```bash
pip install -r ../requirements-django.txt
pytest -c pytest.ini
python manage.py check
```

Expected (security hardening included):

```text
30 passed
System check identified no issues
```

`python manage.py test` may report 0 tests because Django suite lives in pytest
(`backend/tests/`). Prefer `pytest -c pytest.ini` for integration coverage.

Combined target: **213** tests when both suites are run (183 engine + 30 Django).

---

## Running a Single Test File

```bash
pytest tests/test_hashing.py
pytest tests/test_metadata.py
pytest tests/test_keyword_search.py
pytest tests/test_browser_analysis.py
pytest tests/test_phase1_scaffold.py
pytest tests/test_ai.py
```

## Running a Single Test Function

```bash
pytest tests/test_hashing.py::TestHashService::test_calculate_hashes -q
```

---

## Running the Demo

```bash
python main.py
```

Expected demo sections:

1. Phase 2 hashing summary
2. Phase 3 metadata summary
3. Phase 4 keyword search summary
4. Phase 5 browser analysis summary
5. Phase 6 timeline reconstruction summary
6. Phase 7 chain-of-custody summary
7. Phase 8 forensic report generation (JSON + PDF under `outputs/reports/`)
8. Phase 9 AI-assisted investigation (disabled + local deterministic fallback)

Sample evidence is under `evidence/sample_case/` (including `evidence/sample_case/ai/`).

---

## Project Test Structure

```
tests/
├── conftest.py                 # Shared service/profile fixtures
├── browser_fixtures.py         # Synthetic browser DB builders
├── test_phase1_scaffold.py
├── test_hashing.py
├── test_metadata.py
├── test_keyword_search.py
├── test_browser_analysis.py
├── test_timeline.py
├── test_custody.py
├── test_reports.py
└── test_ai.py
```

Django suite:

```
backend/tests/
├── conftest.py
├── test_auth_and_cases.py
└── test_integration_api.py
```

Notes:

- Shared fixtures belong in `conftest.py`
- Synthetic browser databases are generated in temp paths during tests
- Committed sample profiles also exist under `evidence/sample_case/browser/` for demos
- AI tests must not require network access or external model servers
- Django tests must not require the engine tests to import Django

---

## Continuous Validation Checklist

Before starting Phase 11 work:

1. Activate the virtual environment
2. `pip install -r requirements.txt`
3. `pytest` (engine)
4. `pip install -r requirements-django.txt` and `cd backend && pytest -c pytest.ini`
5. Optionally `python main.py`
6. Confirm no existing engine tests were broken
