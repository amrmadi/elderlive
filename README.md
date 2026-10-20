# ElderLife AI — Backend & Frontend

![Backend tests](https://img.shields.io/badge/backend%20tests-205%20passing-brightgreen)
![Frontend tests](https://img.shields.io/badge/frontend%20tests-43%20passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11--3.13%20recommended-blue)
![Node](https://img.shields.io/badge/node-20%2B-blue)

> **Graduation project.** A monitoring system that helps caregivers look after
> elderly people living at home.

This repository contains the **backend API** and the **frontend web app**.
Together they cover the care-management half of the project: residents, care
plans, check-ins, alerts, access control, and analytics.

AI model training, the Power BI reporting layer, and the Docker deployment
configuration are **not part of this repository** — see
[Not in this repository](#not-in-this-repository).

---

## Start here

| If you want to… | Read |
|---|---|
| **Run it on your own machine** | [Quick start](#quick-start) |
| **Know what is finished** | [What works today](#what-works-today) |
| **Work on the remaining tasks** | [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| **See every endpoint** | [`backend/README.md`](backend/README.md) |
| **Understand the frontend** | [`frontend/README.md`](frontend/README.md) |

---

## Quick start

The backend and frontend are **two separate processes**. Start the backend
first. Run commands from the repository root unless stated otherwise.

### 1. Backend

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

# Create the schema. Run from backend/ — alembic.ini lives there.
cd backend
$env:DATABASE_URL = "sqlite+pysqlite:///./elderlife_local_dev.db"
..\.venv\Scripts\alembic.exe upgrade head

# Start the API (keep DATABASE_URL set in this shell)
..\.venv\Scripts\uvicorn.exe backend.app.main:app --reload
```

- API: <http://localhost:8000>
- Interactive docs: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>

> `DATABASE_URL` defaults to **PostgreSQL**. The SQLite line above is the quick
> path and needs nothing extra installed.

### 2. Demo data

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.seed_demo --reset
```

This creates four throwaway logins, all with password `DemoPassw0rd!23`:

| Email | Role |
|---|---|
| `admin@demo.elderlife.example` | admin — sees everything |
| `caregiver.a@demo.elderlife.example` | primary caregiver for Margaret |
| `caregiver.b@demo.elderlife.example` | secondary for Margaret, **primary for George** |
| `resident@demo.elderlife.example` | elderly login for Margaret |

> The seed script **refuses to run** when `ENVIRONMENT=production`.

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173
```

The frontend defaults to `http://localhost:8000`, so no `.env` file is needed.

> ⚠️ **Open the app at `http://localhost:5173`, not `http://127.0.0.1:5173`.**
> The backend's CORS allowlist names `localhost` explicitly, so the `127.0.0.1`
> form is blocked by the browser and every request will fail.

### 4. Sign in and look around

Open <http://localhost:5173> and sign in as
`caregiver.a@demo.elderlife.example`. Then sign out and sign in as
`caregiver.b@demo.elderlife.example` — each sees a **different** list of
residents. That difference is the access control working, enforced on the
server, not hidden by the UI.

---

## What works today

| Area | State | How it is verified |
|---|---|---|
| Database schema | ✅ 19 application tables | `alembic upgrade head` creates them |
| Auth + JWT | ✅ login, register, current user | covered by tests |
| Access control | ✅ enforced **server-side** | unassigned caregivers get `403` on profiles, care plans, check-ins and alerts |
| Elderly profiles | ✅ list / read / create / update | covered by tests |
| Care plans + items | ✅ API and UI | end-to-end workflow test |
| Check-ins | ✅ with schedule support | covered by tests |
| Activity events | ✅ with a `simulated` source value | covered by tests |
| Alerts | ✅ create → acknowledge → resolve, with timestamps | including double-acknowledge rejection |
| Alert rules engine | ✅ event → alert, with severity and deduplication | covered by tests |
| Analytics KPIs | ✅ `/analytics/kpis` and `.csv` | returns `value: null` when the data cannot support a number |
| AI capability endpoints | ✅ `/ai/predictors*` | every predictor reports `is_ready: false` (no model is shipped here) |
| Frontend | ✅ React + TypeScript + Vite | `tsc -b` exits 0, `npm run build` exits 0, **43 tests pass** |
| Backend tests | ✅ | **205 automated tests pass** |

Everything in this table has been run on this machine.

---

## Technology stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | React + TypeScript + Vite | Modern, typed, fast dev server |
| Backend | Python + FastAPI | Simple, fast, auto-generated API docs |
| Database | PostgreSQL (SQLite for local dev and tests) | Reliable relational database |
| ORM + migrations | SQLAlchemy + Alembic | Standard Python database tools |
| Auth | JWT (`PyJWT`) + argon2 password hashing | Signed access tokens |

---

## Repository structure

```
ElderLife-AI/
├── backend/                  # FastAPI application (REST API)
│   ├── alembic/              #   database migrations
│   ├── app/                  #   application code
│   │   ├── api/routers/      #     endpoint definitions
│   │   ├── core/             #     config, security
│   │   ├── models/           #     SQLAlchemy tables
│   │   ├── schemas/          #     Pydantic request/response types
│   │   └── services/         #     alert rules, KPI calculations
│   ├── scripts/seed_demo.py  #   synthetic [DEMO] data
│   └── tests/                #   backend test suite
├── frontend/                 # React + TypeScript + Vite web app
│   └── src/
│       ├── api/              #   typed API client
│       ├── auth/             #   login state
│       ├── components/       #   shared UI
│       └── pages/            #   dashboard, residents, alerts
├── ai/                       # Typed AI interfaces used by the backend
│   ├── base.py               #   result types + the Predictor protocol
│   └── registry.py           #   predictor registry (no model is shipped)
├── .env.example              # Placeholder environment variables — copy to .env
├── pytest.ini                # Test configuration
├── CONTRIBUTING.md           # How to run, test, and submit work
└── README.md                 # This file
```

> **Why is there an `ai/` folder?** The backend's AI router imports it
> (`from ai.base import ...`), so the API cannot start without it. It holds only
> the typed interfaces and reports "no model available" for every predictor —
> it is a **backend dependency**, not AI work. See
> [`ai/README.md`](ai/README.md).

---

## Not in this repository

These parts of the wider project exist elsewhere and are deliberately **not**
published here:

| Area | Status |
|---|---|
| AI model training (fall detection, activity recognition, anomaly detection) | Not included |
| Public research datasets (SisFall, UCI HAR, CASAS) | Not included |
| Power BI reporting and CSV exports | Not included |
| Docker Compose deployment configuration | Not included |

Because no model is shipped, the AI endpoints honestly report
`is_ready: false` for every predictor, and calling one returns **`503
MODEL_NOT_LOADED`**. The API never fabricates a prediction — that rule is
enforced in code and covered by tests. See
[Honesty rules](#honesty-rules).

---

## Running the tests

```powershell
# Backend — 205 tests. Uses in-memory SQLite, needs no database server.
.\.venv\Scripts\python.exe -m pytest -q

# Frontend — 43 tests, plus a type check and a production build
cd frontend
npm test
npx tsc -b
npm run build
```

Useful subsets while developing:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -v -k access    # access control
.\.venv\Scripts\python.exe -m pytest backend\tests -v -k alert     # alert rules
```

**A green test run is not proof a feature works.** If you change the seed
script, the schema, or anything the API serves, start the server and try it.

---

## Honesty rules

These rules are enforced in code and covered by tests, not just written down.

1. **Simulated data is never presented as real.** Demo rows are marked
   `[DEMO]`; demo events use `source="simulated"`.
2. **A missing measurement is not an emergency.** Missing check-ins are capped
   at `low` severity. Alert `severity` is an **operational triage priority** —
   how urgently a person should look — **not** a validated medical risk score.
3. **An unavailable capability says so.** A predictor with no model reports
   `is_ready: false` and returns `503 MODEL_NOT_LOADED` rather than a guess.
   A KPI whose denominator is zero returns `value: null` with
   `is_measurable: false` and a stated reason rather than an invented number.
4. **No secrets, no personal data.** Real credentials live only in your local
   `.env`. `.env.example` holds placeholders.
5. **Nothing is "done" until it has been run.** Report what you measured,
   including results that are worse than expected.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `No config file 'alembic.ini' found` | alembic run from the wrong folder | `cd backend` first |
| `connection refused` to the database | no PostgreSQL running | Use SQLite: `$env:DATABASE_URL = "sqlite+pysqlite:///./elderlife_local_dev.db"` |
| `ModuleNotFoundError: No module named 'backend'` | wrong working directory | Run from the repository root |
| `ModuleNotFoundError: No module named 'ai'` | running the backend from outside the repository root | The API imports the local `ai` package; run from the repository root |
| Every frontend request fails with a CORS error | you opened `127.0.0.1:5173` instead of `localhost:5173` | Use <http://localhost:5173> |
| Login returns `422` for a demo account | the account predates the demo-domain fix | Re-seed: `python -m backend.scripts.seed_demo --reset` |
| `Microsoft Visual C++ 14.0 or greater is required` | a dependency has no wheel for your Python version | Install Python 3.12 and recreate `.venv` |
| Port `8000` / `5173` already in use | another process holds the port | Stop the other process, or change the port |
| AI endpoint returns `503 MODEL_NOT_LOADED` | no model is shipped in this repository | Expected — see [Not in this repository](#not-in-this-repository) |

---

## Documentation

| Document | Contents |
|---|---|
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to run, test, and submit work — plus the open task list |
| [backend/README.md](backend/README.md) | Backend layout, endpoints, and conventions |
| [frontend/README.md](frontend/README.md) | Frontend layout and how it talks to the API |
| [ai/README.md](ai/README.md) | The typed AI interfaces the backend depends on |

---

## A note on Python 3.15

The machine this was built on runs Python 3.15, which is new enough that several
packages have no pre-built wheel, so `pip` tries to compile them from source and
fails on Windows with `Microsoft Visual C++ 14.0 or greater is required`. The
project pins versions that **do** have 3.15 wheels, so it works today.

**If you can use Python 3.12, do** — it removes the constraint entirely.

```powershell
winget install --id Python.Python.3.12 --exact
```
