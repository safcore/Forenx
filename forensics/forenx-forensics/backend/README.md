# ForenX Django / DRF Integration Backend
#
# This package is a host adapter around the standalone forensic engine (`app/`).
# It does NOT reimplement forensic algorithms.
#
# This is the ONLY runtime API for the Forensx monorepo.
# Do not use the older scaffold at `Forensx/backend/` for local development.

## Locations

| Piece | Path |
|-------|------|
| Backend (this package) | `forensics/forenx-forensics/backend` |
| Forensics engine | `forensics/forenx-forensics/app` |
| Frontend (separate) | `frontend/forenx-app` |
| Backend port | `8000` |
| Frontend port | `5173` |
| Local database | SQLite (`backend/db.sqlite3`) |
| Production database | PostgreSQL via `DATABASE_URL` |

## Quick start (Windows PowerShell)

From `forensics/forenx-forensics`:

```powershell
# 1) Activate environment
.\.venv\Scripts\Activate.ps1

# First-time / after pull: install deps
pip install -r requirements.txt
pip install -r requirements-django.txt

# Optional: copy env template and set a local secret
# copy .env.example .env

# 2) PYTHONPATH must include repo root + backend
$env:PYTHONPATH = "$PWD;$PWD\backend"

# 3) Migrate
cd backend
python manage.py migrate

# 4) Start API (local only — not for production)
python manage.py runserver
```

Local API: http://localhost:8000  
Admin: http://localhost:8000/admin/

Production uses Gunicorn + a TLS reverse proxy. See `docs/PRODUCTION.md`.

## Configuration

Environment is loaded from `forensics/forenx-forensics/.env` (and `backend/.env` if present).
See `.env.example` for variable names only — never commit real secrets.

Important variables:

- `DEBUG` / `DJANGO_DEBUG`
- `SECRET_KEY` / `DJANGO_SECRET_KEY`
- `ALLOWED_HOSTS` / `DJANGO_ALLOWED_HOSTS`
- `DATABASE_URL` (omit for SQLite; `postgresql://...` for production)
- `CORS_ALLOWED_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`
- `FORENX_STORAGE_ROOT` / `FORENX_MAX_UPLOAD_BYTES`
- `FORENX_AI_*` (advisory AI; network disabled by default)

## Auth

- `POST /api/auth/register/`
- `POST /api/auth/login/` — accepts `{ "email", "password" }` **or** `{ "username", "password" }`
- `POST /api/auth/refresh/`
- `GET  /api/auth/me/`

## Core routes

- `GET/POST /api/cases/`
- `GET/PATCH /api/cases/<id>/`
- `GET/POST /api/cases/<case_id>/evidence/`
- `POST /api/evidence/<id>/hash/`
- `GET  /api/evidence/<id>/metadata/` (read-only stored result)
- `POST /api/evidence/<id>/metadata/analyze/`
- `POST /api/evidence/<id>/keywords/`
- `GET  /api/evidence/<id>/browser/` (read-only stored result)
- `POST /api/evidence/<id>/browser/analyze/`
- `GET  /api/evidence/<id>/timeline/` (read-only stored result)
- `POST /api/evidence/<id>/timeline/analyze/`
- `GET  /api/evidence/<id>/custody/`
- `GET  /api/evidence/<id>/custody/verify/`
- `POST /api/evidence/<id>/report/`
- `POST /api/evidence/<id>/ai/`
- `GET  /api/reports/<id>/`
- `GET  /api/reports/<id>/download/`

See `docs/django-integration.md` and `docs/PRODUCTION.md`.

## Tests

Engine (must stay green without Django imports in `app/`):

```powershell
# from forensics/forenx-forensics
pytest
```

Django integration:

```powershell
cd backend
pytest -c pytest.ini
python manage.py check --deploy
```
