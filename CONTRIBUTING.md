# Contributing to ElderLife AI

This is a **graduation project**, so clarity matters more than cleverness. This
document tells you how to run the project, how to check your work, and which
tasks are still open.

This repository contains the **backend** and **frontend**. AI model training,
Power BI reporting, and the Docker deployment configuration are out of scope —
see [Not in this repository](README.md#not-in-this-repository).

---

## Contents

- [Before you start](#before-you-start)
- [Running the project](#running-the-project)
- [Running the tests](#running-the-tests)
- [Project rules you must follow](#project-rules-you-must-follow)
- [Open tasks](#open-tasks)
- [How to submit your work](#how-to-submit-your-work)
- [Troubleshooting](#troubleshooting)

---

## Before you start

| Tool | Version used here | Notes |
|---|---|---|
| Node.js | 20+ (verified on v24.13.1) | for the frontend |
| npm | 10+ (verified on 11.8.0) | comes with Node |
| Python | 3.11–3.13 recommended | 3.15 works, with a caveat |
| Git | any recent | |

**A note on Python 3.15.** The machine this was built on runs Python 3.15, which
is new enough that several packages have no pre-built wheel, so `pip` tries to
compile them from source and fails on Windows with
`Microsoft Visual C++ 14.0 or greater is required`. The project pins versions
that **do** have 3.15 wheels. **If you can use Python 3.12, do** — it removes
the constraint entirely.

```powershell
winget install --id Python.Python.3.12 --exact
```

---

## Running the project

The backend and frontend are **two separate processes**. Start the backend first.
Run every command from the **repository root** unless stated otherwise.

### 1. Backend

```powershell
# One-time: create the environment and install dependencies
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

# Create the database schema. Run from backend/ — alembic.ini lives there.
cd backend
$env:DATABASE_URL = "sqlite+pysqlite:///./elderlife_local_dev.db"
..\.venv\Scripts\alembic.exe upgrade head

# Start the API (keep DATABASE_URL set in this shell)
..\.venv\Scripts\uvicorn.exe backend.app.main:app --reload
```

- API: <http://localhost:8000>
- Interactive docs: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>

> `DATABASE_URL` defaults to **PostgreSQL**, which may not be installed on your
> machine. The SQLite line above is the quick path and needs nothing extra.

### 2. Demo data

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.seed_demo --reset
```

This prints four throwaway logins, all with password `DemoPassw0rd!23`:

| Email | Role |
|---|---|
| `admin@demo.elderlife.example` | admin — sees everything |
| `caregiver.a@demo.elderlife.example` | primary caregiver for Margaret |
| `caregiver.b@demo.elderlife.example` | secondary for Margaret, **primary for George** |
| `resident@demo.elderlife.example` | elderly login for Margaret |

Signing in as `caregiver.a` and then `caregiver.b` is the quickest way to see the
access control working: each sees a **different** list of residents, enforced on
the server.

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

---

## Running the tests

```powershell
# Backend — 205 tests, uses in-memory SQLite, needs no database server
.\.venv\Scripts\python.exe -m pytest -q

# Frontend — 43 tests
cd frontend
npm test

# Type check and production build
npx tsc -b
npm run build
```

### Quick subset while developing

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -v -k access     # access control
.\.venv\Scripts\python.exe -m pytest backend\tests -v -k alert      # alert rules
.\.venv\Scripts\python.exe -m pytest backend\tests -v -k analytics  # KPI maths
```

**A green test run is not proof the feature works.** If you change the seed
script, a migration, or anything the API serves, **start the server and try it**.

---

## Project rules you must follow

These are not style preferences — they are the rules that keep the project
trustworthy. They are enforced in code and covered by tests where possible.

### 1. Never present simulated data as real

- Demo rows are marked `[DEMO]`; demo events use `source="simulated"`.
- The database has a `simulated` value in its event-source list specifically so
  demo data can never be mistaken for a real reading.

### 2. A missing measurement is not an emergency

Missing check-ins or silence must never be escalated as a dangerous event — they
are capped at `low` severity. Alert `severity` is an **operational triage
priority** (how urgently a person should look), **not** a validated medical risk.

### 3. An unavailable capability says so

No model is shipped in this repository, so every predictor reports
`is_ready: false` and calling one returns **`503 MODEL_NOT_LOADED`**. It must
never return a plausible-looking guess.

The same rule applies to KPIs: when the denominator is zero the API returns
`value: null` with `is_measurable: false` and a stated reason, rather than
inventing a number.

### 4. No secrets, no personal data

- Real credentials never live in the repository — only in your local `.env`.
- `.env.example` contains **placeholders only**.
- Never enter real personal or medical information into the demo.

### 5. Nothing is "done" until it has been run

Update the README with what you **measured**, including results that are worse
than expected. Negative results are still results; hidden ones are not.

---

## Open tasks

Each task lists a definition of done. Pick one, open a branch, and keep the
change focused.

### T1 — Real-time alerts (WebSocket) ⬜

**Goal:** a new alert appears in the UI without a page refresh.

- Add `/ws/alerts` to the backend, respecting the **same access rules** as the
  REST endpoints. A caregiver must only receive alerts for residents they are
  assigned to — do not leak other residents' alerts over the socket. This is the
  part most likely to go wrong; test it explicitly.
- Subscribe from the frontend and prepend new alerts to the list.
- **Done when:** creating an alert in one browser session makes it appear in
  another, and an unassigned caregiver receives nothing.

### T2 — Care plan editing in the UI ⬜

**Goal:** a caregiver can create and complete care-plan tasks from the app.

- The API supports care plans and their items; check what the frontend already
  exposes before adding endpoints.
- **Done when:** a plan can be created in the UI, its items completed, and the
  change survives a backend restart.

### T3 — Frontend linting and formatting ⬜

**Goal:** consistent code style.

- `package.json` currently maps `lint` to `tsc --noEmit` — there is **no ESLint
  or Prettier config**.
- **Done when:** ESLint and Prettier are configured and the whole `src/` tree
  passes.

### T4 — Browser flow test ⬜

**Goal:** automated coverage of a full user journey.

- The 43 frontend tests cover the HTTP client, format helpers, and page states,
  but not one happy-path journey from login to alert acknowledgement.
- **Done when:** a test drives login → residents → alert acknowledgement and
  asserts the rendered output.

### T5 — CI pipeline ⬜

**Goal:** tests run automatically on every push.

- Add `.github/workflows/` running `pytest`, `npm test`, `npx tsc -b`, and
  `npm run build`.
- **Done when:** the workflow is green on a fresh clone.

### T6 — Password reset and token refresh ⬜

**Goal:** a more complete authentication flow.

- Authentication is currently a single `SECRET_KEY` JWT with no refresh-token
  rotation and no password-reset flow.
- **Done when:** a user can reset a forgotten password, and access tokens can be
  refreshed without re-entering credentials.

### T7 — Load testing the API ⬜

**Goal:** know how the API behaves beyond a single user.

- PostgreSQL behaviour has been verified for schema correctness, not under
  concurrency or contention.
- **Done when:** measured results are written down, including the point at which
  latency becomes unacceptable.

---

## How to submit your work

1. **Branch off.** Use a descriptive name: `feature/ws-alerts`, `fix/alert-scoping`.
2. **Keep commits focused.** One task per branch where you can.
3. **Run the checks before you push:**
   ```powershell
   .\.venv\Scripts\python.exe -m pytest -q
   cd frontend; npx tsc -b; npm test
   ```
4. **Do not remove working tests** to make a suite pass. If a test is genuinely
   wrong, say so in the pull request and explain why.
5. **Write an honest commit message.** Say what changed, what you ran, and what
   you observed. If something is unverified, say that.
6. **Update the docs** you invalidated — especially the README's
   "What works today" table.

### Commit message style

```
Short summary in the imperative mood

What changed and why. Mention the commands you actually ran and their
results, including any number you are claiming.

If something is deliberately NOT done or NOT verified, say so here.
```

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
| `Microsoft Visual C++ 14.0 or greater is required` | no Python wheel for your version | Install Python 3.12 and recreate `.venv` |
| Port `8000` / `5173` already in use | another process holds the port | Stop the other process, or change the port |
| AI endpoint returns `503 MODEL_NOT_LOADED` | no model is shipped in this repository | Expected — not a bug |
