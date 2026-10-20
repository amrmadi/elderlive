# ElderLife AI — Development Roadmap

> Plain-language plan. Each milestone lists its tasks, the finished result, and how we know
> it works. Status values: ⬜ not started · 🟦 in progress · ✅ done.
> **Never mark something "done" until it actually runs.**

---

## Phase overview

| # | Milestone | Covers | Status |
|---|---|---|---|
| M0 | Project skeleton | folders, docs, templates | ✅ |
| M1 | Database | PostgreSQL, SQLAlchemy, Alembic | ✅ (PostgreSQL verified: 20 tables, no drift) |
| M2 | Backend core | FastAPI, CRUD, validation | ✅ |
| M3 | Frontend core | React + TS + Vite, API client, dashboard | ✅ builds, 43 tests pass, verified against the live backend |
| M4 | Care plans | plans, goals, schedules | 🟦 API + UI done; covered end-to-end by the workflow test |
| M5 | Alerts | rules, notifications, real-time updates | 🟦 rules engine + lifecycle done; WebSocket ⬜ |
| M6 | AI / ML | datasets, preprocessing, 3 models, integration | 🟨 fall detection trained (F1 0.80); activity + anomaly still interfaces only |
| M7 | Analytics | SQL views, exports, Power BI | 🟦 8 views run on real PostgreSQL; exports done; no `.pbix` |
| M8 | Testing | pytest, vitest, model tests, CI | 🟦 289 backend + AI + 43 frontend tests passing; no CI |
| M9 | Deployment | Dockerfiles, full compose, final docs | ✅ stack built and run; all 3 services healthy |

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
- [x] Decide how PostgreSQL runs (Docker **or** native Windows install) — **Docker**
- [x] Create `backend/` with `pyproject.toml` / `requirements.txt`
- [x] Virtual environment `.venv` + pinned dependencies
- [x] SQLAlchemy 2.0 models: `residents`, `care_plans`, `care_tasks`, `sensor_readings`,
      `events`, `alerts`, `model_versions`
- [x] Alembic initialized; first migration; `alembic upgrade head` works
- [x] Seed script using **synthetic, clearly-labeled test records** (not real people)

**Done when:** `alembic upgrade head` creates all tables on a fresh database.
**Verified:** on a fresh `postgres:16-alpine` container, `alembic upgrade head`
created **20 tables** (19 ORM tables + `alembic_version`), `alembic current`
reports `596dcc02ab32 (head)`, and `alembic check` reports no new operations.

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
**Verified:** the app builds (`tsc -b` exits 0, `npm run build` exits 0) and its
43 tests pass. It has now also been exercised **against the live backend over
HTTP**: login succeeds from the browser's origin with correct CORS, and the
profile, alert, alert-rule, and analytics endpoints all return `200` with
per-user scoping applied server-side. In this environment that was done with
real HTTP requests rather than a driven browser, so the visual pass remains a
manual step — see the demo walkthrough in the README.

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
- [x] Alert inbox UI with filters and acknowledge action *(verified against the
      live backend over HTTP)*
- [ ] (Optional) e-mail/webhook notification channel

**Done when:** a simulated fall event produces an alert that appears live in the UI.
*(Not yet met: the WebSocket does not exist, so the UI is not live.)*

## M6 — AI / ML

**Goal:** three working, honest models wired into the API.

- [x] Document **SisFall** in `docs/datasets/` *before* downloading —
      [`sisfall.md`](datasets/sisfall.md), every field verified against the archive
- [ ] Document the other two (CASAS, UCI HAR) before downloading — still `To verify`
- [x] Download the fall-detection dataset into `data/raw/` (manually, not committed)
- [x] Preprocessing script → `ai/fall_detection/preprocess.py` (outputs git-ignored)
- [x] **Fall detection** — RandomForest on windows, with a measured evaluation report
      (**F1 0.80** on 6 unseen adult subjects; see
      [`ai/fall_detection/README.md`](../ai/fall_detection/README.md))
- [ ] **Activity recognition** — baseline model on UCI HAR (then optional deep model)
- [ ] **Behavioral anomaly detection** — per-resident routine baseline (e.g. IsolationForest /
      statistics on activity sequences from CASAS)
- [x] Model version, metrics and training date recorded in the artefact metadata and served
      by the API (`model_versions` DB table remains for the activity/anomaly models)
- [x] Typed inference interfaces — `ai/base.py` (`FallDetectionResult`,
      `ActivityResult`, `AnomalyResult`, `ModelInfo`, `Predictor` protocol,
      `ModelNotLoadedError`) and `ai/registry.py`
- [x] Expose `/ai/*` endpoints; return `503 MODEL_NOT_LOADED` while a predictor has no
      model (`GET /ai/predictors`, `GET /ai/predictors/{name}`,
      `POST /ai/predictors/{name}/check`)
- [x] Serving predictor that loads the trained model — `ai/fall_detection/predictor.py`
- [x] Unit tests that run without a database or dataset —
      `ai/tests/test_interfaces.py`, `ai/tests/test_preprocess.py`,
      `ai/tests/test_fall_predictor.py` and `backend/tests/test_ai_api.py`

**Honesty rule enforced in code:** a predictor with no model reports `metrics = None`,
`is_ready = False` and raises `ModelNotLoadedError` rather than returning a guess. Once a
model is trained, `metrics` carries only the values actually measured. Simulated or
imported-dataset input is flagged `is_simulated=True`, so public research data and demo data
can never be presented as a live measurement of a resident.

**Done when:** each model beats (or clearly documents) its baseline on a held-out test set,
and the metrics are written down — including failures.
*(Partially met: fall detection is trained and evaluated on subject-wise held-out data, and
its **worse** cross-population result on elderly subjects is published rather than hidden.
Activity recognition and anomaly detection are still untrained, so for them no metric is
reported and none is invented. Fall detection uses SisFall instead of the originally-planned
UP-Fall, whose full distribution is ~812 GB.)*

## M7 — Analytics

**Goal:** Power BI-compatible reporting without extra services.

- [x] `analytics/sql/` views: daily check-ins, alerts, caregiver
      acknowledgement times, care-plan adherence, activity summary, model runs,
      resident rollup, KPI definitions (7 views + 1 catalogue view)
- [x] `analytics/export_analytics.py` producing CSV per view on demand, with a
      `_manifest.json` recording when/where/how many rows — **executed against
      real PostgreSQL**: 8 CSVs written, manifest records
      `postgresql+psycopg` / `elderlife`. A view with no rows
      (`analytics_model_runs`) still writes its header and `row_count: 0`
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
*(Partly met: the CSVs now exist, exported from a real PostgreSQL database with a
manifest recording their provenance, so Power BI Desktop can import them. The
Power BI step itself is unverified — no `.pbix` exists and none is claimed.)*

## M8 — Testing

**Goal:** confidence that changes don't break things.

- [ ] `tests/` layout: `unit/`, `integration/`, `e2e/` — tests currently live in
      `backend/tests/`, `ai/tests/`, and `tests/`, plus colocated
      `frontend/src/**/*.test.ts(x)`
- [ ] Backend coverage target: meaningful, not vanity numbers
- [x] Frontend component tests — 43 tests (HTTP client, format helpers, page
      states). *One happy-path browser flow test is still missing.*
- [x] AI interface tests: no network, no dataset download (`ai/tests/test_interfaces.py`)
- [x] End-to-end API workflow test: register → profile → care plan → check-in →
      simulated event → alert → acknowledge → resolve → unassigned caregiver 403
      (`backend/tests/test_workflow_end_to_end.py`)
- [x] AI API tests: capability listing, `503 MODEL_NOT_LOADED`, unknown-name 404
      (`backend/tests/test_ai_api.py`)
- [x] Seed-script tests: demo credentials actually log in, reset stays surgical
      (`backend/tests/test_seed_demo.py`)
- [ ] GitHub Actions (or local script): lint + test on every push

**Done when:** one command runs the full suite and it is green.
*`pytest -q` runs **289** backend + AI tests and they pass; `npm test` runs
**43** frontend tests and they pass. They are still two commands, not one, and
there is no CI yet.*

## M9 — Deployment

**Goal:** anyone can start the whole system with one command.

- [x] `backend/Dockerfile` — python:3.12-slim, non-root user, `/health` healthcheck
- [x] `frontend/Dockerfile` — multi-stage Node build → nginx 1.27 runtime
- [x] `frontend/nginx.conf` — SPA fallback, gzip, security headers, optional `/api/` proxy
- [x] Complete `docker-compose.yml` — db + backend + frontend, healthchecks,
      `depends_on: condition: service_healthy`, named volume, private network
- [x] `.dockerignore` at the root and in `frontend/` (no `.venv`, `node_modules`,
      `data/raw`, `.env`, or model artifacts in any build context)
- [x] Production build served correctly (`npm run build` → nginx serves `dist/`)
- [x] Env vars documented in `.env.example`, including `SECRET_KEY`
- [x] README quick-start for Windows, troubleshooting table, demo walkthrough,
      and the real-vs-simulated distinction
- [x] **Actually build and run the stack** — built and started; `db`, `backend`,
      and `frontend` all reach `healthy`
- [x] Migrations applied to real PostgreSQL (`596dcc02ab32`, no drift)
- [x] Analytics SQL applied to real PostgreSQL (`ON_ERROR_STOP=1`; 8 views)
- [x] Verified over HTTP: health, demo logins, server-side access control, CORS
- [x] Backup/restore note for the database volume

**Backing up and restoring the database.** All persistent state lives in the
`elderlife_pgdata` named volume. A plain logical dump is the safest way to move
it, and it does not depend on Docker's volume internals:

```powershell
# Backup — writes a portable SQL dump to the current folder
docker compose exec -T db pg_dump -U elderlife_dev -d elderlife > backup.sql

# Restore into a running (ideally empty) database
Get-Content backup.sql | docker compose exec -T db psql -U elderlife_dev -d elderlife
```

`docker compose down` stops the containers but **keeps** the volume, so the data
survives a normal restart. `docker compose down -v` **deletes** it and is
irreversible — the next `up` starts from an empty database, and migrations and
seeding must be re-run. For a byte-for-byte copy of the volume itself, `docker
run --rm -v elderlife_pgdata:/data -v ${PWD}:/backup alpine tar czf
/backup/pgdata.tar.gz -C /data .` works but is only safe while the database is
stopped.

**Done when:** `docker compose up` on a clean machine brings the app up end-to-end.

*Status: **done**, verified by running it. `docker compose config` interpolates,
`docker compose build` produces both images, and `docker compose up -d` brings
all three services to `healthy`. `alembic upgrade head` created 20 tables in the
`postgres:16-alpine` container with no schema drift, the demo seed loaded and all
four logins were accepted, the 8 analytics views were created and queried, and
the frontend was exercised against the live backend including CORS.*

*Running the stack found two defects that static validation had missed — nginx
was sending no security headers (and two conflicting `Cache-Control` headers),
and the demo seed produced an acknowledged alert whose acknowledgement preceded
its creation. Both are fixed and covered by regression tests: a structural check
in `tools/validate_nginx.py`, and a timestamp-ordering test in
`backend/tests/test_seed_demo.py`.*

*The remaining item is the backup/restore note for the `elderlife_pgdata`
volume.*

---

## Suggested order of the next phases

M1 → M2 → M3 (thin vertical slice: data in DB, API serves it, UI shows it)
then M4 → M5 (visible features for the demo), then M6 (AI), M7 (analytics),
M8 (tests along the way, not only at the end), M9 (deployment).
