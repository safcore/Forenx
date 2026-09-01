# ForenX production, backup, and recovery

ForenX is finished as a production-ready investigation host. Do not add new forensic features.

Use this document for deployment, HTTPS, PostgreSQL, static files, backups, and restore.

## Runtime topology

```
HTTPS reverse proxy (TLS termination)
        ↓
Gunicorn (config.wsgi) + WhiteNoise static files
        ↓
Django / DRF JWT API
        ↓
PostgreSQL  +  persistent evidence/report storage
```

Do **not** use `python manage.py runserver` in production.

## Environment

Copy `forensics/forenx-forensics/.env.example` and `frontend/forenx-app/.env.example`.
Set values locally or in the host secret store. Never commit `.env`.

Required backend names:

- `DEBUG=False`
- `SECRET_KEY` (unique, 50+ characters; `DJANGO_SECRET_KEY` is accepted)
- `ALLOWED_HOSTS`
- `DATABASE_URL` (`postgresql://user:password@host:5432/forenx`)
- `CORS_ALLOWED_ORIGINS` (exact HTTPS origins of the SPA)

Also set `CSRF_TRUSTED_ORIGINS` to the same HTTPS origins when cookies/CSRF apply.
JWT access uses the `Authorization: Bearer` header.

Required frontend name:

- `VITE_API_URL` — baked in at `npm run build`. Use the HTTPS API origin including `/api`, for example `https://api.example.com/api`.

Persistent storage:

- `FORENX_STORAGE_ROOT` must be a durable volume that survives process restart and redeployment.

## Production server

From `forensics/forenx-forensics`:

```powershell
$env:PYTHONPATH = "$PWD;$PWD\backend"
$env:DEBUG = "False"
# SECRET_KEY, ALLOWED_HOSTS, DATABASE_URL, CORS_ALLOWED_ORIGINS must already be set

cd backend
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
gunicorn --config gunicorn.conf.py
```

Gunicorn binds to `127.0.0.1:8000` by default (`GUNICORN_BIND`). Put Nginx or an equivalent reverse proxy in front and terminate TLS there. Forward `X-Forwarded-Proto: https`.

Frontend production build:

```powershell
cd frontend/forenx-app
$env:VITE_API_URL = "https://api.example.com/api"
npm run build
```

Serve `dist/` over HTTPS. The SPA and API must communicate over HTTPS in production.

## Static files

- `STATIC_URL=/static/`
- `STATIC_ROOT=backend/staticfiles`
- WhiteNoise serves collected files from Gunicorn

## PostgreSQL

Leave `DATABASE_URL` unset for local SQLite development and tests.

Production example:

```
DATABASE_URL=postgresql://forenx:PASSWORD@127.0.0.1:5432/forenx?sslmode=require
```

`sslmode` in the query string is passed through to Django. Models use UUID, JSON, and standard Django fields and are PostgreSQL-compatible without a data-model change.

## Backup and recovery

### Database

Take a daily PostgreSQL dump and retain at least 14 days (keep monthly copies longer if policy requires it).

Backup:

```bash
pg_dump -Fc -d "$DATABASE_URL" -f "/backups/forenx-$(date -u +%Y%m%d).dump"
```

Restore (service stopped or database empty):

```bash
pg_restore --clean --if-exists -d "$DATABASE_URL" /backups/forenx-YYYYMMDD.dump
python manage.py migrate
```

SQLite development copies are not a production backup.

### Evidence

Original acquired files live under `$FORENX_STORAGE_ROOT/evidence/` (default `storage/evidence/` in development).

- Mount this directory on persistent disk (not an ephemeral container layer).
- Back it up daily with the same retention as the database (filesystem snapshot or `rsync`/`rclone` to offline storage).
- Restore by replacing the volume contents, then confirming each evidence `stored_path` still resolves.

Evidence must not disappear on application restart or redeployment.

### Reports

Generated reports live under `$FORENX_STORAGE_ROOT/reports/`. Prefer backing them up with evidence.

If a derived report file is lost, an authorized investigator can regenerate it from stored acquisition data. Regeneration writes a new report artifact; it does not replace original evidence.

### Forensic immutability

1. Original acquired evidence must remain immutable.
2. Forensic analysis must operate against stored acquisition data.
3. Analysis must never silently overwrite original evidence.
4. Chain-of-custody events are append-only.

Hash, keyword, browser, timeline, metadata, report, and AI flows read the stored original. They persist `AnalysisRun` / report / custody records; they do not rewrite the acquired file.

## Security notes that must not be weakened

- JWT on all investigation endpoints; auditors remain read-only.
- CORS is an explicit allow-list (`CORS_ALLOW_ALL_ORIGINS` is false).
- Production error responses omit stack traces, filesystem paths, secrets, and evidence storage paths.
- Upload size defaults to 50 MiB (`FORENX_MAX_UPLOAD_BYTES`).
- Browser, timeline, and metadata analysis run only on explicit POST `/analyze/` routes. GET is read-only.

## Checks before release

```powershell
cd forensics/forenx-forensics/backend
pytest

cd ../../../frontend/forenx-app
npm run build

cd ../../forensics/forenx-forensics/backend
python manage.py check --deploy
python manage.py collectstatic --noinput
```

Infrastructure-only deploy warnings (for example TLS termination owned by the reverse proxy) may remain and should be documented in the host runbook. Do not disable authentication or authorization to silence them.
