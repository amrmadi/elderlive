# ElderLife AI — Development Roadmap

> Plain-language plan. Each milestone lists its tasks, the finished result, and how we know
> it works. Status values: ⬜ not started · 🟦 in progress · ✅ done.
> **Never mark something "done" until it actually runs.**

---

## Phase overview

| # | Milestone | Covers | Status |
|---|---|---|---|
| M0 | Project skeleton | folders, docs, templates | 🟦 (this phase) |
| M1 | Database | PostgreSQL, SQLAlchemy, Alembic | ⬜ |
| M2 | Backend core | FastAPI, CRUD, validation | ⬜ |
| M3 | Frontend core | React + TS + Vite, API client, dashboard | ⬜ |
| M4 | Care plans | plans, goals, schedules | ⬜ |
| M5 | Alerts | rules, notifications, real-time updates | ⬜ |
| M6 | AI / ML | datasets, preprocessing, 3 models, integration | ⬜ |
| M7 | Analytics | SQL views, exports, Power BI | ⬜ |
| M8 | Testing | pytest, vitest, model tests, CI | ⬜ |
| M9 | Deployment | Dockerfiles, full compose, final docs | ⬜ |

---

## M0 — Project skeleton (Phase 1) 🟦

**Goal:** a clean, documented repository where every later phase has a obvious home.

- [x] Inspect environment and tools
- [x] Create folder structure
- [x] Root `README.md` with directory purposes
- [x] `.gitignore` (secrets, data, model artifacts, junk)
- [x] `.env.example` with placeholders only
- [x] `docs/architecture.md` with Mermaid diagram
- [x] `docs/api-contract.md`
- [x] `docs/roadmap.md` (this file)
- [x] Dataset documentation template + one page per dataset
- [ ] User confirms the plan → then M1 starts

**Done when:** files exist, review passes, and no real secrets or data are present.

---

## M1 — Database

**Goal:** a schema we can persist data in, with reproducible migrations.

Tasks:
- [ ] Decide how PostgreSQL runs (Docker **or** native Windows install)
- [ ] Create `backend/` with `pyproject.toml` / `requirements.txt`
- [ ] Virtual environment `.venv` + pinned dependencies
- [ ] SQLAlchemy 2.0 models: `residents`, `care_plans`, `care_tasks`, `sensor_readings`,
      `events`, `alerts`, `model_versions`
- [ ] Alembic initialized; first migration; `alembic upgrade head` works
- [ ] Seed script using **synthetic, clearly-labeled test records** (not real people)

**Done when:** `alembic upgrade head` creates all tables on a fresh database.

## M2 — Backend core

**Goal:** a running FastAPI server with real CRUD.

- [ ] App factory, config from `.env`, structured logging
- [ ] `GET /health` including DB check
- [ ] Residents CRUD with Pydantic validation + the error envelope from the contract
- [ ] Pagination helper; global exception handler
- [ ] Auto-generated docs at `/docs` reviewed by hand
- [ ] `pytest` smoke tests for health + residents

**Done when:** `uvicorn backend.app:app` runs and the pytest suite passes.

## M3 — Frontend core

**Goal:** a typed React app that talks to the backend.

- [ ] Scaffold Vite + React + TypeScript in `frontend/`
- [ ] Lint + format config (ESLint, Prettier)
- [ ] One typed API client reading `VITE_API_BASE_URL`
- [ ] Pages: Dashboard, Residents list/detail (placeholders first, then live data)
- [ ] Loading / empty / error states for every data view
- [ ] `vitest` component tests for the API client and key components

**Done when:** `npm run dev` shows live data fetched from the running backend.

## M4 — Care plans

**Goal:** caregivers can record and track care plans.

- [ ] Domain model + endpoints from the contract (`/care-plans`)
- [ ] Care-plan UI: create, edit, complete scheduled tasks
- [ ] Validation rules (dates, overlapping tasks)
- [ ] Integration tests

**Done when:** a plan can be created in the UI and survives a backend restart.

## M5 — Alerts

**Goal:** important events become visible, trackable alerts.

- [ ] Alert model + list/acknowledge endpoints
- [ ] Rule engine: event → alert (severity, deduplication, cooldown)
- [ ] WebSocket `/ws/alerts` for real-time UI updates
- [ ] Alert inbox UI with filters and acknowledge action
- [ ] (Optional) e-mail/webhook notification channel

**Done when:** a simulated fall event produces an alert that appears live in the UI.

## M6 — AI / ML

**Goal:** three working, honest models wired into the API.

- [ ] Document **all three datasets** in `docs/datasets/` *before* downloading
- [ ] Download datasets into `data/raw/` (manually, not committed)
- [ ] Preprocessing scripts → `data/processed/`
- [ ] **Fall detection** — baseline model (e.g. RandomForest on windows), evaluation report
- [ ] **Activity recognition** — baseline model on UCI HAR (then optional deep model)
- [ ] **Behavioral anomaly detection** — per-resident routine baseline (e.g. IsolationForest /
      statistics on activity sequences from CASAS)
- [ ] Model registry: version, metrics, training date stored in `model_versions`
- [ ] Expose `/ai/*` endpoints; return `503 MODEL_NOT_LOADED` until models exist
- [ ] Unit tests that run without a database

**Done when:** each model beats (or clearly documents) its baseline on a held-out test set,
and the metrics are written down — including failures.

## M7 — Analytics

**Goal:** Power BI-compatible reporting without extra services.

- [ ] `analytics/sql/` views: daily activity summary, alert counts, per-resident trends
- [ ] `analytics/exports/` scripts producing CSV + Parquet on demand
- [ ] `GET /analytics/summary` for the dashboard
- [ ] A short guide: how to connect Power BI Desktop to the export files / SQL view
- [ ] Screenshot of the Power BI report in `docs/` once it exists

**Done when:** Power BI Desktop imports an exported file and renders real data.

## M8 — Testing

**Goal:** confidence that changes don't break things.

- [ ] `tests/` layout: `unit/`, `integration/`, `e2e/`
- [ ] Backend coverage target: meaningful, not vanity numbers
- [ ] Frontend component tests; one happy-path browser flow test
- [ ] AI tests: fixed seeds, no network, no dataset download in CI
- [ ] GitHub Actions (or local script): lint + test on every push

**Done when:** one command runs the full suite and it is green.

## M9 — Deployment

**Goal:** anyone can start the whole system with one command.

- [ ] `backend/Dockerfile`, `frontend/Dockerfile`
- [ ] Complete `docker-compose.yml` (db + backend + frontend, healthchecks)
- [ ] Production build served correctly; env vars documented
- [ ] README quick-start written for a fresh machine
- [ ] Backup/restore note for the database volume

**Done when:** `docker compose up` on a clean machine brings the app up end-to-end.

---

## Suggested order of the next phases

M1 → M2 → M3 (thin vertical slice: data in DB, API serves it, UI shows it)
then M4 → M5 (visible features for the demo), then M6 (AI), M7 (analytics),
M8 (tests along the way, not only at the end), M9 (deployment).
