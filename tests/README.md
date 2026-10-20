# `tests/` — Automated tests

**Purpose:** catch mistakes before they become demo-day surprises.

**Planned layout (milestone M8):**
```
tests/
├── unit/          # pure logic: AI functions, helpers (no DB, no network)
├── integration/   # API + database together (uses a throwaway test database)
└── e2e/           # full flows through the running app
```

- Backend tests: `pytest` (the backend's own `tests/` may hold fast unit tests; shared
  integration tests live here).
- Frontend tests: `vitest` + React Testing Library, run inside `frontend/`.
- AI tests must run **without** downloading datasets; they use `data/sample/` files.

**Status:** empty — no tests written yet. (Writing tests starts in M2 and continues
throughout; M8 consolidates them.)
