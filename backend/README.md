# `backend/` — API server

**Purpose:** everything the browser should not do directly: validation, database
access, business rules, and calling the AI modules.

- **Stack:** Python, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic, psycopg
  (PostgreSQL driver).
- **Must NOT contain:** ML training code, frontend code, or real credentials
  (config comes from `.env` via a settings module).

**Status:** built and tested — **205 automated tests pass**.

## Layout

```
backend/
├── alembic/                  # database migrations
│   └── versions/
├── app/
│   ├── api/
│   │   ├── routers/          # endpoint definitions
│   │   └── v1.py             # router assembly
│   ├── core/
│   │   ├── config.py         # settings, read from the environment
│   │   └── security.py       # password hashing, JWT
│   ├── db/                   # engine, session, Base
│   ├── models/               # SQLAlchemy tables
│   ├── schemas/              # Pydantic request/response types
│   ├── services/             # alert rules, KPI calculations
│   └── main.py               # FastAPI app factory
├── scripts/
│   └── seed_demo.py          # synthetic [DEMO] data
└── tests/                    # test suite
```

## Running it

```powershell
# From the repository root — one-time setup
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

# Create the schema. Run from backend/ — alembic.ini lives here.
cd backend
$env:DATABASE_URL = "sqlite+pysqlite:///./elderlife_local_dev.db"
..\.venv\Scripts\alembic.exe upgrade head

# Start the API
..\.venv\Scripts\uvicorn.exe backend.app.main:app --reload
```

The interactive API docs are auto-generated at <http://localhost:8000/docs>.

> **Why run alembic from `backend/`?** `alembic.ini` lives there and finds the
> migration folder relative to itself. From the repository root you get
> "No config file 'alembic.ini' found".

## Endpoint groups

All routes are under `/api/v1`.

| Group | Routes | Notes |
|---|---|---|
| Health | `GET /health` | includes a real database check |
| Auth | `/auth/login`, `/auth/register`, `/auth/me` | JWT bearer tokens |
| Elderly profiles | `/elderly-profiles` | list is paged: `{items, total, page, page_size}` |
| Caregivers | `/caregivers` | assignments and roles |
| Care plans | `/care-plans` | plans and their items |
| Check-ins | `/check-ins` | includes schedule support |
| Activity events | `/activity-events` | `source` can be `simulated` |
| Alerts | `/alerts` | create → acknowledge → resolve, with timestamps |
| Alert rules | `/alert-rules` | event → alert, with severity and deduplication |
| Analytics | `/analytics/kpis`, `/analytics/kpi-definitions`, `/analytics/kpis.csv` | `start` and `end` are **required** |
| AI | `/ai/predictors`, `/ai/predictors/{name}`, `/ai/predictors/{name}/check` | returns `503 MODEL_NOT_LOADED` — no model is shipped |

## Access control

Enforced **server-side**, not in the UI. A caregiver only sees residents they are
assigned to; an unassigned caregiver receives **`403`** on profiles, care plans,
check-ins, and alerts. Administrators see everything.

This is covered by `tests/test_access_control.py` and is deliberately tested
against the API rather than the interface, because hiding a button is not
security.

## Honesty rules enforced here

- Alert `severity` is an **operational triage priority**, not a validated medical
  risk score.
- Missing check-ins are capped at `low` severity. **A data gap is not an
  emergency.**
- A KPI whose denominator is zero returns `value: null` with
  `is_measurable: false` and a stated reason, never an invented number.
- A predictor with no model returns **`503 MODEL_NOT_LOADED`**, never a guess.

## Tests

```powershell
# From the repository root. Uses in-memory SQLite — no database server needed.
.\.venv\Scripts\python.exe -m pytest backend\tests -q

# A subset
.\.venv\Scripts\python.exe -m pytest backend\tests -v -k access
```

Each test gets its own fresh in-memory database, so tests cannot leak state into
each other. The trade-off, stated honestly: **SQLite is not PostgreSQL**, so
PostgreSQL-specific behaviour (some types, concurrency, `ON DELETE` semantics) is
not covered by these tests.

## Seeding demo data

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.seed_demo --reset
```

Options:

| Flag | Effect |
|---|---|
| `--reset` | delete previously seeded demo rows first |
| `--dry-run` | report what would happen without writing |
| `--force` | override the safety check |

The script **refuses to run** when `ENVIRONMENT=production`.
