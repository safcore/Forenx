# Developer Guide

## Project Structure

```
forenx-forensics/
├── app/                 # Engine source (Django-free)
│   ├── hashing/
│   ├── metadata/
│   ├── keyword/
│   ├── browser/
│   ├── timeline/
│   ├── custody/
│   ├── reports/
│   ├── ai/
│   ├── services/
│   ├── schemas/
│   ├── models/
│   └── utils/
├── backend/             # Django/DRF host adapter (Phase 10)
├── tests/               # Engine pytest suite
├── docs/
├── evidence/
├── storage/             # Runtime evidence/report store
├── outputs/
├── assets/
├── logs/
└── main.py              # Engine demo entry point only
```

---

## Coding Standards

- Python **3.12+**
- PEP 8 formatting
- Google-style docstrings on public modules, classes, and functions
- Prefer composition through services rather than cross-feature imports
- No business logic in `main.py`, `__init__.py`, or tests

---

## Typing Requirements

- Annotate all public functions, methods, and constructors
- Prefer `str | Path` for filesystem inputs
- Prefer concrete Pydantic schema return types from services
- Avoid untyped `dict` / `Any` in public APIs

---

## Logging

```python
from app.utils.logger import get_logger, setup_logging

setup_logging()          # once per process (CLI / Django ready())
logger = get_logger(__name__)
logger.info("operation started")
```

Rules:

- No `print()` inside `app/`
- Do not call `setup_logging()` at import time from feature modules
- Log start/finish, warnings, and errors with structured messages

---

## Testing

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
pytest tests/test_hashing.py -q
```

Guidelines:

- Prefer fixtures in `tests/conftest.py` when shared
- Keep builders (e.g. synthetic browser DBs) in dedicated helper modules
- Never assert on forensic algorithms by changing production business logic in tests

See [testing.md](testing.md).

---

## Schema Usage

- Service methods must return Pydantic models from `app.schemas`
- Use `model_dump(mode="json")` at host boundaries (Django / REST)
- Missing optional metadata returns `None`, not dummy strings

---

## Exception Handling

Raise subclasses of `ForenXError` from `app.utils.exceptions`.

Do not raise for “no matches found” or missing optional EXIF fields.

Catch library-specific errors where practical and wrap into domain exceptions.

---

## How to Create a New Forensic Module

1. Add feature package under `app/<feature>/` with algorithms only.
2. Add Pydantic schemas under `app/schemas/<feature>.py`.
3. Add orchestrator `app/services/<feature>_service.py`.
4. Export the service from `app/services/__init__.py`.
5. Add tests under `tests/`.
6. Document the public API in `docs/api.md`.
7. Keep `main.py` as a thin demo only.

Suggested dependency direction:

```
services → feature packages → utils/schemas
```

Avoid:

```
feature packages → services   # creates cycles / layering violations
```

---

## Naming Conventions

| Item | Convention | Example |
|------|------------|---------|
| Packages | snake_case | `hash_service.py` |
| Classes | PascalCase | `HashService` |
| Functions | snake_case | `calculate_hashes` |
| Constants | UPPER_SNAKE | `HASH_CHUNK_SIZE` |
| Schemas | PascalCase nouns | `HashResult` |
| Tests | `test_*.py` | `test_hashing.py` |

---

## Evidence Safety Checklist

- Open browser SQLite databases via temporary read-only copies
- Never write into evidence paths
- Prefer `pathlib.Path`
- Keep configuration in `app/utils/config.py`
