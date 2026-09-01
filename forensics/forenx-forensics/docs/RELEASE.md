# ForenX release, demo, and presentation

ForenX is complete. There is no Phase 21. Use this note for demos, portfolio write-ups, and presentations.

## What to show

ForenX is a digital-forensics investigation host: JWT auth, cases, evidence acquisition, hashing, integrity, keyword search, browser/timeline/metadata analysis, reports, chain of custody, analysis history, live dashboard, and advisory AI.

The Python engine in `app/` stays framework-agnostic. Django in `backend/` is the only runtime API. The React SPA in `frontend/forenx-app` talks to it over `VITE_API_URL`.

## Demo walkthrough

1. Sign in (investigator or lead). Confirm the dashboard is read-only live data.
2. Create a case.
3. Upload evidence. Confirm hashes and the first custody events.
4. Run hash comparison and integrity verification.
5. Run keyword search.
6. Click the explicit analysis buttons for browser, timeline, and metadata (POST `/analyze/`). Viewing stored results does not re-run analysis.
7. Generate a JSON/PDF report and download it.
8. Open chain of custody and analysis history. Confirm append-only events and no original-file overwrite.
9. Optional: AI assist. Label it advisory; it does not replace forensic engines.

## Portfolio talking points

- Separation of forensic engines from the API host
- Production configuration via environment variables (no committed secrets)
- PostgreSQL-ready `DATABASE_URL` with SQLite for local/dev
- Persistent evidence storage and documented backup/restore
- Side-effecting analysis is explicit POST; GET is read-only
- Role-based authorization (auditors cannot run analysis)
- HTTPS in production via reverse proxy + Gunicorn, not Django `runserver`

## Source of truth docs

- Architecture: `docs/architecture.md`
- API: `docs/api.md`
- Django host: `docs/django-integration.md`
- Production / backup: `docs/PRODUCTION.md`
- Backend runbook: `backend/README.md`
