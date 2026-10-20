# ElderLife AI

> **Current status: the application runs, is tested, and has been deployed with
> Docker Compose.** Backend, frontend, database schema, alert rules, analytics
> SQL, and the AI *interfaces* all exist and are verified. **No AI model has been
> trained**, so no prediction is real — see
> [Real predictions vs simulated events](#real-predictions-vs-simulated-events).
> The container stack has been built and run on this machine: PostgreSQL 16,
> the API, and the nginx frontend all come up healthy, migrations apply to real
> PostgreSQL, and the frontend was exercised against the live backend. See
> [What actually works today](#what-actually-works-today).

ElderLife AI is a beginner-friendly graduation project: a system that helps monitor the
well-being of elderly people at home. It aims to:

- detect **falls** from sensor data,
- recognize daily **activities** (walking, resting, cooking, ...),
- spot **behavioral anomalies** (unusual routines that may indicate health changes),
- manage **residents and care plans**,
- raise **alerts** for caregivers,
- and produce **analytics** that can be opened in Power BI.

The care-management half is built and works on real stored data. The AI half is
**designed but not trained**; the API says so out loud rather than guessing.

---

## What actually works today

| Area | State | How it is verified |
|---|---|---|
| Database schema | ✅ 19 application tables (+ `alembic_version`) | `alembic upgrade head` creates them; column-by-column comparison against the models shows **no drift** |
| Backend API (FastAPI) | ✅ auth, profiles, care plans, check-ins, events, alerts, analytics, AI capability routes | **242 automated tests pass** |
| Access control | ✅ enforced **server-side** | Unassigned caregivers get `403` on profiles, care plans, check-ins, alerts, and alert acknowledgement |
| Alert lifecycle | ✅ create → acknowledge → resolve, with timestamps | Covered by tests, including double-acknowledge rejection |
| Frontend (React + TS) | ✅ builds and is unit-tested | `tsc -b` exits 0, `npm run build` exits 0, **43 tests pass** |
| Analytics SQL | ✅ 8 views; names real tables/columns | **148 column references** checked against the models |
| AI **interfaces** | ✅ typed, tested | **25 interface tests**; every predictor reports `is_ready: false` |
| AI **models / predictions** | ❌ **do not exist** | `/ai/predictors/*/check` returns `503 MODEL_NOT_LOADED` |
| Docker Compose stack | ✅ **built and run; all three services healthy** | PostgreSQL 16, API, nginx; see [Docker](#docker-optional) |
| Migrations on **real PostgreSQL** | ✅ applied, **no drift** | `alembic upgrade head` → `596dcc02ab32`; `alembic check` → no new operations |
| Analytics SQL on real PostgreSQL | ✅ **all 8 views created and queried** | Applied with `ON_ERROR_STOP=1`; views return rows from seeded data |
| Frontend against a live backend | ✅ **verified** | Login → scoped data → all pages `200`, with correct CORS |

---

## Technology stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | React + TypeScript + Vite | Modern, typed, fast dev server |
| Backend | Python + FastAPI | Simple, fast, auto-generated API docs |
| Database | PostgreSQL (SQLite for local dev/tests) | Reliable relational database |
| ORM / Migrations | SQLAlchemy + Alembic | Standard Python DB tools |
| AI / ML | Python (`ai/` package) | Datasets are tabular/sensor based |
| Analytics | SQL views + CSV exports | Easy to load into Power BI |
| Deployment | Docker Compose | One command to run the whole stack |

---

## Repository structure

```
ElderLife-AI/
├── frontend/                 # React + TypeScript + Vite web app
│   ├── Dockerfile            #   multi-stage: Node build -> nginx runtime
│   ├── nginx.conf            #   SPA serving + optional /api proxy
│   └── .dockerignore
├── backend/                  # FastAPI application (REST API)
│   ├── Dockerfile            #   python:3.12-slim, non-root, healthcheck
│   ├── alembic/              #   database migrations
│   ├── app/                  #   application code
│   ├── scripts/seed_demo.py  #   synthetic [DEMO] data
│   └── tests/                #   backend test suite
├── ai/                       # Machine-learning code
│   ├── base.py               #   typed inference interfaces (result types)
│   ├── registry.py           #   predictor registry (all unavailable today)
│   ├── tests/                #   interface tests, no dataset needed
│   ├── fall_detection/       #   fall detection (planned: SisFall)
│   ├── activity_recognition/ #   activity classification (planned: UCI HAR)
│   └── behavioral_analysis/  #   routine / anomaly detection (planned: CASAS)
├── data/                     # Datasets (mostly git-ignored)
│   ├── raw/                  #   original downloaded files — never edited
│   ├── processed/            #   cleaned data produced by scripts
│   └── sample/               #   small hand-made examples for tests
├── analytics/
│   ├── sql/                  #   SQL views/queries feeding Power BI
│   ├── export_analytics.py   #   CSV export script
│   └── exports/              #   generated files (git-ignored)
├── docs/                     # Architecture, API contract, roadmap, datasets
├── tests/                    # Cross-cutting tests
├── tools/                    # Offline validators (see "Verification tools")
├── docker-compose.yml        # db + backend + frontend, with healthchecks
├── .dockerignore             # Keeps the build context small and secret-free
├── .env.example              # Placeholder environment variables — copy to .env
└── README.md                 # This file
```

Every major folder contains its own `README.md` explaining what belongs there.

---

## Prerequisites

| Tool | Required for | Status on this machine |
|---|---|---|
| Node.js 20+ | frontend | ✅ installed (v24.13.1) |
| npm | frontend | ✅ installed (11.8.0) |
| Python 3.11–3.13 | backend, AI | ⚠️ 3.15.0 installed (see note below) |
| pip | Python packages | ✅ installed (26.2.1) |
| Git | version control | ✅ installed (2.53.0) |
| Docker Desktop | the Compose stack | ✅ installed (29.0.1; engine running via WSL2) |
| PostgreSQL | local database | ✅ available via the `db` container (16-alpine); no host `psql` |

**Note on Python 3.15:** it is very new, so some packages have no pre-built wheel
for it and `pip` tries to compile them from source, which fails on Windows with
`Microsoft Visual C++ 14.0 or greater is required`. The project pins versions that
**do** have 3.15 wheels (`pydantic>=2.12`, `psycopg[binary]>=3.3.6`,
`SQLAlchemy>=2.1.5`) so the backend works today. Installing Python 3.12 removes
that constraint entirely — and the Docker image uses 3.12, so the pins are not
needed inside a container.

To install Python 3.12 (requires an **Administrator** PowerShell, then a reboot):

```powershell
winget install --id Python.Python.3.12 --exact --accept-package-agreements --accept-source-agreements
```

Then recreate the virtual environment with it:

```powershell
python3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

To install Docker Desktop (also needs an **Administrator** PowerShell, then a reboot):

```powershell
winget install --id Docker.DockerDesktop --exact --accept-package-agreements --accept-source-agreements
```

---

## Getting started on Windows

The backend and frontend run as two separate processes. Start the backend first.
Every command below is run from the **repository root** unless stated otherwise.

### 1. Backend API

Create the virtual environment once:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

The default `DATABASE_URL` targets **PostgreSQL**, which is not installed here.
To run without PostgreSQL, point the app at SQLite — this is verified to work:

```powershell
cd backend
$env:DATABASE_URL = "sqlite+pysqlite:///./elderlife_local_dev.db"
..\.venv\Scripts\alembic.exe upgrade head          # creates all the tables
```

> **Why `cd backend` first?** `alembic.ini` lives in `backend/` and finds the
> migration folder relative to itself. Running `alembic` from the repository root
> fails with "No config file 'alembic.ini' found". This also applies to the Docker
> command later.

Then, with `DATABASE_URL` still set in that shell, start the API:

```powershell
..\.venv\Scripts\uvicorn.exe backend.app.main:app --reload
```

- API: <http://localhost:8000>
- Interactive docs: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

Run the tests (they use in-memory SQLite, so no database is needed):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

### 2. Seed synthetic demo data

From the repository root. The script **refuses to run** when
`ENVIRONMENT=production`, and only ever touches rows it created:

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.seed_demo --reset
```

It prints the accounts it created:

| Email | Password | Role |
|---|---|---|
| `admin@demo.elderlife.example` | `DemoPassw0rd!23` | admin — sees everything |
| `caregiver.a@demo.elderlife.example` | `DemoPassw0rd!23` | primary caregiver for Margaret |
| `caregiver.b@demo.elderlife.example` | `DemoPassw0rd!23` | secondary for Margaret, primary for George |
| `resident@demo.elderlife.example` | `DemoPassw0rd!23` | elderly login for Margaret |

> **These are throwaway demo credentials, not secrets.** They are deliberately
> obvious and are the *only* password that appears anywhere in this repository.
> Never reuse them, and never put a real password in `.env.example`.

All demo rows are marked `[DEMO]`, and demo activity events use
`source="simulated"`. See [`backend/README.md`](backend/README.md) for the
`--reset` / `--force` / `--dry-run` options.

> The demo domain is `demo.elderlife.example`, **not** `.local`. `.local` is a
> reserved TLD that the API's email validator rejects, so accounts there could be
> created but never log in. A regression test now guards this.

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173
```

The frontend defaults to `http://localhost:8000`, so no `.env` file is required.
Useful checks:

```powershell
npx tsc -b         # type check
npm test           # unit tests
npm run build      # production build into dist/
```

See [`frontend/README.md`](frontend/README.md).

---

## Docker

**Verified status:** the stack has been **built and run on this machine** and all
three services come up healthy. What was actually executed and observed:

| Step | Result |
|---|---|
| `docker compose config` | Interpolates and validates |
| `docker compose build` | Both images built (`elderlife-backend`, `elderlife-frontend`) |
| `docker compose up -d` | `db` → healthy, `backend` → healthy, `frontend` → healthy |
| `docker compose exec backend alembic upgrade head` | `Running upgrade -> 596dcc02ab32` |
| `alembic current` / `alembic check` | `596dcc02ab32 (head)` / "No new upgrade operations detected" |
| `\dt` in PostgreSQL | **20 tables** (19 ORM tables + `alembic_version`) |
| `seed_demo --reset` | Four demo logins created and verified |
| Analytics SQL applied with `ON_ERROR_STOP=1` | **8 views created**; all return rows from seeded data |
| Access control over HTTP | Unassigned caregiver `403`; assigned `200`; admin `200`; anonymous `401` |
| Login through the browser's CORS path | `200`, `Access-Control-Allow-Origin: http://localhost:5173`; disallowed origin gets no header |
| nginx responses | Security headers and a single `Cache-Control` on `/`, assets, and deep links |

Two real defects were found and fixed by running the stack, which static checks
had missed: nginx was emitting **no security headers at all** (and two conflicting
`Cache-Control` headers), because nginx discards server-level `add_header`
inside a location that declares its own; and the demo seed created an
**acknowledged alert whose acknowledgement preceded its creation**, producing a
negative median acknowledgement time in the analytics KPI. Both now have
regression tests.

### What the stack contains

| Service | Image | Port | Healthcheck |
|---|---|---|---|
| `db` | `postgres:16-alpine` | 5432 | `pg_isready` |
| `backend` | built from `backend/Dockerfile` (python:3.12-slim, non-root) | 8000 | `curl /health` (does a real `SELECT 1`) |
| `frontend` | built from `frontend/Dockerfile` (Node build → nginx 1.27) | 5173 → 80 | `wget --spider 127.0.0.1` |

The frontend healthcheck probes `127.0.0.1` rather than `localhost`: inside that
container `localhost` resolves to IPv6 `::1` first while nginx listens on IPv4,
and the resulting "connection refused" held the container permanently unhealthy.

`backend` waits for `db` to be **healthy**, and `frontend` waits for `backend` to
be **healthy**, via `depends_on: condition: service_healthy`. Data lives in the
named volume `elderlife_pgdata`, which survives `docker compose down` but not
`docker compose down -v`.

### Running it

```powershell
copy .env.example .env       # then edit the values (see the secret note below)
docker compose up --build -d

# Create the schema, then load the demo data:
docker compose exec backend alembic upgrade head
docker compose exec backend python -m backend.scripts.seed_demo --reset
```

Open <http://localhost:5173> and sign in with a demo account above.

```powershell
docker compose logs -f backend     # watch logs
docker compose down                # stop, keep the database
docker compose down -v             # stop and delete the database
```

> **A secret is required for anything beyond a demo.** `SECRET_KEY` signs login
> tokens. `.env.example` ships an obvious placeholder, and the backend **refuses
> to start** with `ENVIRONMENT=production` while it is still set. Generate a real
> one before deploying anywhere:
>
> ```powershell
> python -c "import secrets; print(secrets.token_urlsafe(48))"
> ```

### How the pieces find each other

- Inside Compose, `backend` reaches the database at host **`db`**, not
  `localhost` — `localhost` inside a container is the container itself.
- The browser loads the app from the host, so the frontend is built with
  `VITE_API_BASE_URL=http://localhost:8000`. This is compiled in at **build time**
  and passed as a build argument.
- To avoid CORS entirely, build the frontend with
  `VITE_API_BASE_URL=/api`; `frontend/nginx.conf` then proxies `/api/` to
  `http://backend:8000`. The proxy block is inert otherwise.

---

## Verification tools

These checks run offline and are honest about their limits; each exits non-zero
on failure. They are a **fast pre-flight**, not a substitute for running the
stack — and they are no longer the only evidence, since the stack itself has now
been built, started, and exercised (see [Docker](#docker)).

```powershell
.\.venv\Scripts\python.exe tools\validate_analytics_sql.py    # SQL names real tables/columns
.\.venv\Scripts\python.exe tools\validate_nginx.py            # nginx.conf structure + add_header inheritance
node tools\validate-compose-real.js                          # compose + Dockerfile paths
```

The nginx validator specifically models nginx's `add_header` inheritance rule:
a security header set at server level is dropped inside any location that
declares its own, so the validator requires the headers to live in
`frontend/security-headers.conf` and be `include`d from every content-serving
location. That class of bug was previously invisible to static checks and only
showed up once the container was running.

The Compose validator needs a YAML parser. If `js-yaml` is not in the project, it
can be run against a temporary install without adding a dependency:

```powershell
$env:NODE_PATH = "$env:TEMP\somewhere\node_modules"; node tools\validate-compose-real.js
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `No config file 'alembic.ini' found` | alembic run from the wrong folder | `cd backend` first — `alembic.ini` lives there |
| `connection refused` / `could not connect to server` | no PostgreSQL running | Use SQLite: `$env:DATABASE_URL = "sqlite+pysqlite:///./elderlife_local_dev.db"` |
| `ModuleNotFoundError: No module named 'backend'` | wrong working directory | Run from the repository root, or set `$env:PYTHONPATH = (Get-Location).Path` |
| Login returns `422` for a demo account | the account predates the demo-domain fix (`.local`) | Re-seed: `python -m backend.scripts.seed_demo --reset` |
| `Microsoft Visual C++ 14.0 or greater is required` | a package has no Python 3.15 wheel | Install Python 3.12 and recreate `.venv` (see Prerequisites) |
| Port `8000` / `5432` / `5173` already in use | another service holds the port | Change the left-hand side of the mapping in `docker-compose.yml`, or stop the other process |
| Backend container starts before the database is ready | missing healthcheck ordering | Already handled: `depends_on` uses `condition: service_healthy` |
| Frontend loads but every request fails | API URL compiled in at build time | Rebuild with the correct `VITE_API_BASE_URL`, then hard-refresh the browser |
| `Docker Desktop is unable to start` | the WSL2 backend has no distro/kernel | Run `wsl --install`, or `wsl --update`, then restart Docker Desktop |
| Frontend container stuck at `health: starting` | nginx probed over IPv6 `localhost` while listening on IPv4 | Healthcheck probes `127.0.0.1` (already fixed in the Dockerfile and Compose) |
| Stale app after a redeploy | browser cached `index.html` | `nginx.conf` already sends `no-cache` for it; hard-refresh once |

---

## Demo walkthrough

A guided tour showing the whole system, using only synthetic data.

1. **Start and seed.** Follow [Getting started](#getting-started-on-windows),
   then run the seeder. It prints the demo accounts.
2. **Sign in** at <http://localhost:5173> as
   `caregiver.a@demo.elderlife.example` / `DemoPassw0rd!23`.
3. **See the residents.** Margaret Example is assigned to this caregiver. Sign in
   as `caregiver.b@demo.elderlife.example` to see a different list — this is the
   access restriction working, enforced by the server, not hidden by the UI.
4. **Care plan.** Open Margaret, view the care plan and its items.
5. **Check-in.** Record a wellbeing check-in. Note that the API stamps who
   recorded it and when.
6. **Alert.** Open the alerts list. Acknowledge an alert, then resolve it. Notice
   the acknowledgement records *who* and *when* — that is what the caregiver KPI
   is computed from.
7. **Prove the AI is honest.** Call the capability endpoint:

   ```powershell
   # Needs a token from the login response.
   curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/ai/predictors
   ```

   Every entry says `is_ready: false`. Asking one to run returns `503` with code
   `MODEL_NOT_LOADED` — it does **not** invent a prediction.
8. **Analytics (PostgreSQL + Docker only).** Apply `analytics/sql/*.sql` and run
   `analytics/export_analytics.py` to produce CSVs for Power BI.

---

## Real predictions vs simulated events

This distinction matters more than anything else in the project, so it is stated
plainly.

**Simulated events — these exist and work.**

- Demo activity events are written with `source="simulated"`.
- The database has a `simulated` value in its event-source list specifically so
  demo data can never be mistaken for a real reading.
- Alert `severity` is an **operational triage priority** — how urgently a person
  should look — not a validated medical risk score.
- A **data gap is never treated as an emergency.** Missing check-ins or silence
  are capped at `low` severity; the system does not guess that silence means harm.

**Real model predictions — these do not exist yet.**

- **No model has been trained. No dataset has been downloaded.**
- `ai/` currently contains typed *interfaces* (`ai/base.py`), a registry
  (`ai/registry.py`), and tests. Every predictor reports `is_ready: false` and
  `metrics: null` — never placeholder numbers.
- `POST /api/v1/ai/predictors/{name}/check` returns **`503 MODEL_NOT_LOADED`**.
- When a model is trained, the predictor is swapped in behind the same interface.
  Until then, the system says "not available" rather than producing a
  plausible-looking answer.

The distinction is enforced in code and covered by tests, not just documented.

---

## Known limitations

- **No AI model is trained.** The three problems are designed, not solved. There
  are no accuracy, precision, or recall numbers to report, and none are invented.
- **PostgreSQL is verified for schema, seeding, and queries — not for load.**
  Migrations, the 20 tables, the analytics views, and the API were all exercised
  against a real `postgres:16-alpine` container. What has **not** been tested is
  behaviour under concurrency, contention, or failover.
- **The analytics views have only been run over demo data.** All 8 views execute
  and return rows against a seeded database. They have never been run at a scale
  where query plans or indexes would matter.
- **No `.pbix` file exists.** Power BI reports cannot be generated without the
  desktop application. CSV exports are produced for it instead.
- **The frontend has been run against the live backend over HTTP**, not yet
  driven through a real browser in this environment. Login, scoped data,
  navigation endpoints, CORS, and API error paths were exercised with real HTTP
  requests; the visual pass is still a manual step (see
  [Demo walkthrough](#demo-walkthrough)).
- **WebSocket / real-time updates are not implemented.** The alert list is
  fetched, not pushed.
- **The seed script is development-only** and refuses to run when
  `ENVIRONMENT=production`.
- **Authentication is a single `SECRET_KEY` JWT** with no refresh-token rotation
  and no password-reset flow.

---

## Datasets

Three public research datasets are planned: **SisFall** (fall detection),
**UCI HAR** (activity recognition), and **CASAS** (behavioural analysis).
**None have been downloaded**, and no model has been trained.

Public research data is kept strictly separate from application user records.
Each dataset will be documented in [`docs/datasets/`](docs/datasets/README.md)
(source URL, license, format, labels, preprocessing, limitations) *before* use.

---

## Documentation

| Document | Contents |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Mermaid diagram + component explanation |
| [docs/api-contract.md](docs/api-contract.md) | API between frontend, backend, AI |
| [docs/roadmap.md](docs/roadmap.md) | Milestones for every phase |
| [docs/datasets/README.md](docs/datasets/README.md) | Dataset documentation template + index |

---

## Honesty rules for this project

1. Features are only described as "working" when they actually run.
2. No fake production data is committed. Demo data is marked `[DEMO]` and
   `source="simulated"`.
3. Real credentials never live in this repository — only in your local `.env`.
4. Datasets and trained model artifacts are not committed to Git.
5. An unavailable AI capability reports itself as unavailable; it never returns
   a plausible-looking guess.
6. A missing measurement is not treated as a dangerous event.
