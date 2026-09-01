# Forensx — Local Development Guide

## Runtime architecture (Phase 1)

```
frontend/forenx-app          →  http://localhost:5173
        │ REST / JWT
        ▼
forensics/forenx-forensics/backend   →  http://localhost:8000   ← ONLY runtime API
        │ Python imports
        ▼
forensics/forenx-forensics/app       ← forensic engine (do not rewrite)
```

| Component | Path | Port |
|-----------|------|------|
| Frontend | `frontend/forenx-app` | 5173 |
| Integrated backend | `forensics/forenx-forensics/backend` | 8000 |
| Forensics engine | `forensics/forenx-forensics/app` | — |
| Local DB | SQLite `forensics/forenx-forensics/backend/db.sqlite3` | — |

### Legacy (do not use as runtime)

`backend/` at the monorepo root is an older/thinner Django scaffold.
It is **not** the Phase 1 runtime API. Do not start it on port 8000.

---

## Backend — start

```powershell
cd forensics\forenx-forensics
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "$PWD;$PWD\backend"
cd backend
python manage.py migrate
python manage.py runserver
```

First-time dependency install (if needed):

```powershell
cd forensics\forenx-forensics
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-django.txt
```

Copy `.env.example` → `.env` and set a local `DJANGO_SECRET_KEY`. Never commit `.env`.

---

## Frontend — start

```powershell
cd frontend\forenx-app
npm install
npm run dev
```

Phase 2 live auth: set `VITE_DEMO_MODE=false` and `VITE_API_URL=http://localhost:8000/api` in `frontend/forenx-app/.env`.  
Set `VITE_DEMO_MODE=true` anytime to use the offline UI demo without the backend.

---

## Health checks

- Django: `python manage.py check` (from `backend` with `PYTHONPATH` set)
- Auth: `POST /api/auth/login/` (`email` or `username` + `password`)
- Cases (auth required): `GET /api/cases/`
