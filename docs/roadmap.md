# ElderLife AI — Development Roadmap

> Plain-language plan. Each milestone lists its tasks, the finished result, and how we know
> it works. Status values: ⬜ not started · 🟦 in progress · ✅ done.
> **Never mark something "done" until it actually runs.**

---

## Phase overview

| # | Milestone | Covers | Status |
|---|---|---|---|
| M0 | Project skeleton | folders, docs, templates | ✅ |
| M1 | Database | PostgreSQL, SQLAlchemy, Alembic | ✅ (SQLite-verified; PostgreSQL run pending) |
| M2 | Backend core | FastAPI, CRUD, validation | ✅ |
| M3 | Frontend core | React + TS + Vite, API client, dashboard | 🟦 builds and 43 tests pass; not yet run against a live backend |
| M4 | Care plans | plans, goals, schedules | 🟦 API done; UI done; not end-to-end verified |
| M5 | Alerts | rules, notifications, real-time updates | 🟦 rules engine + lifecycle done; WebSocket ⬜ |
| M6 | AI / ML | datasets, preprocessing, 3 models, integration | ⬜ research done; no training yet |
| M7 | Analytics | SQL views, exports, Power BI | 🟦 views + exports written; not run on PostgreSQL; no `.pbix` |
| M8 | Testing | pytest, vitest, model tests, CI | 🟦 191 backend + 43 frontend tests passing; no CI |
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

- [x] Scaffold Vite + React + TypeScript in `frontend/`
- [ ] Lint + format config (ESLint, Prettier) — **only `tsc --noEmit`; no ESLint/Prettier config exists**
- [x] One typed API client reading `VITE_API_BASE_URL`
- [x] Pages: Dashboard, Residents list/detail (placeholders first, then live data)
- [x] Loading / empty / error states for every data view
- [x] `vitest` tests for the API client and key components — 43 tests in
      3 files; the HTTP client, the presentation helpers, and the page states

**Done when:** `npm run dev` shows live data fetched from the running backend.
*(Not yet met: `tsc -b`, `npm run build` and `npm test` all pass, but the app
has never been run against a live backend — see the honesty note below.)*

## M4 — Care plans

**Goal:** caregivers can record and track care plans.

- [ ] Domain model + endpoints from the contract (`/care-plans`)
- [ ] Care-plan UI: create, edit, complete scheduled tasks
- [ ] Validation rules (dates, overlapping tasks)
- [ ] Integration tests

**Done when:** a plan can be created in the UI and survives a backend restart.

## M5 — Alerts

**Goal:** important events become visible, trackable alerts.

- [x] Alert model + list/acknowledge endpoints
- [x] Rule engine: event → alert (severity, deduplication, cooldown) —
      `backend/app/services/alert_rules.py`, explainable and configurable
- [x] Alert lifecycle: acknowledge / resolve / dismiss + timeline endpoint
- [ ] WebSocket `/ws/alerts` for real-time UI updates
- [x] Alert inbox UI with filters and acknowledge action *(built; not yet run
      against a live backend)*
- [ ] (Optional) e-mail/webhook notification channel

**Done when:** a simulated fall event produces an alert that appears live in the UI.
*(Not yet met: the WebSocket does not exist, so the UI is not live.)*

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

- [x] `analytics/sql/` views: daily check-ins, alerts, caregiver
      acknowledgement times, care-plan adherence, activity summary, model runs,
      resident rollup, KPI definitions (7 views + 1 catalogue view)
- [x] `analytics/export_analytics.py` producing CSV per view on demand, with a
      `_manifest.json` recording when/where/how many rows *(code complete; not
      yet executed against PostgreSQL)*
- [x] `--check-columns`: every `table.column` a view references is verified to
      exist in the migrated schema (148 references, 20 tables), with a negative
      control in the test suite so the check cannot silently pass
- [x] `GET /analytics/kpis`, `/analytics/kpi-definitions`, `/analytics/kpis.csv`
      *(the draft's `/analytics/summary` path was never built — see
      [`api-contract.md`](api-contract.md) §4)*
- [x] A short guide: how to connect Power BI Desktop to the export files / SQL
      view — [`powerbi-guide.md`](powerbi-guide.md)
- [ ] Screenshot of the Power BI report in `docs/` once it exists — **no report
      exists, so there is no screenshot**

**Done when:** Power BI Desktop imports an exported file and renders real data.
*(Not yet met. No `.pbix` exists and none is claimed.)*

## M8 — Testing

**Goal:** confidence that changes don't break things.

- [ ] `tests/` layout: `unit/`, `integration/`, `e2e/` — tests currently live in
      `backend/tests/` and `tests/`, plus colocated `frontend/src/**/*.test.ts(x)`
- [ ] Backend coverage target: meaningful, not vanity numbers
- [x] Frontend component tests — 43 tests (HTTP client, format helpers, page
      states). *One happy-path browser flow test is still missing.*
- [ ] AI tests: fixed seeds, no network, no dataset download in CI
- [ ] GitHub Actions (or local script): lint + test on every push

**Done when:** one command runs the full suite and it is green.
*194 backend + 43 frontend tests pass, but no single command runs both, and
there is no CI.*

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
