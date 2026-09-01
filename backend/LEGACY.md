# Legacy / alternate Django scaffold

This directory (`Forensx/backend`) is **not** the runtime API for the Forensx application.

## Use instead

**Integrated backend:** `forensics/forenx-forensics/backend`  
**Forensics engine:** `forensics/forenx-forensics/app`  
**Frontend:** `frontend/forenx-app`

See monorepo `DEVELOPMENT.md` for start commands.

## Why this folder remains

Kept for reference / historical scaffolding (thin cases/auth API).
Do **not** start this project on port `8000` while developing the integrated stack.
Do **not** point `VITE_API_URL` at this backend for Phase 1+.
