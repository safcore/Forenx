# ForenX — AI-Assisted Digital Forensics Investigation Platform

Premium enterprise frontend for digital forensics investigators, law enforcement, CERT/CSIRT, and SOC teams.

## Quick start

```bash
cp .env.example .env   # or use included .env
npm install
npm run dev
```

Open http://localhost:5173

**Demo mode** (`VITE_DEMO_MODE=true`): sign in with any email + password (≥6 chars). No backend required.

**Production**: set `VITE_DEMO_MODE=false` and point `VITE_API_URL` at your Django API.

## Auth (backend contract)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/auth/login/` | Obtain JWT |
| POST | `/api/auth/register/` | Register |
| POST | `/api/auth/refresh/` | Refresh access token |
| GET | `/api/auth/me/` | Current user |

## Routes (all wired — no dead links)

- `/login`
- `/dashboard`
- `/cases` · `/cases/new` · `/cases/:caseId` (+ evidence / timeline / custody / reports)
- `/evidence` · `/evidence/:evidenceId`
- `/hash-verification`
- `/timeline` · `/custody` · `/reports` · `/analytics`
- `/profile` · `/settings`

## Architecture notes

- React only consumes REST APIs. Forensic algorithms stay in the Python engine.
- Hash / metadata / custody are **authoritative**. AI is **advisory** only.
- Evidence upload flow: Upload → Storage → Hash → Metadata → DB → Custody.
- Keyword, browser, timeline, AI, reports are **separate** operations.
- Cookie **values** are never displayed — metadata only.
- Chain of custody is labeled **tamper-evident**, never “immutable”.

## Stack

React 18 · TypeScript · Vite · Tailwind v4 · Framer Motion · TanStack Query · Axios · React Hook Form + Zod · Recharts · Lucide · Radix UI

## Status (incremental)

**Done**
- Design system, layouts, auth + JWT refresh
- Dashboard, Cases list, Create case, Case detail shell
- Evidence list, Hash verification workstation
- Timeline / Custody / Reports / Analytics / Profile / Settings shells
- Shared: PageHeader, EmptyState, Skeletons, HashDisplay
- API modules: auth, cases, evidence (+ error helper)

**Next**
- Evidence detail + upload progress UI
- Live React Query hooks against backend
- Keyword / Browser analysis workspaces
- Full custody ledger visualization
- Report download via backend
- Command palette (⌘K)
