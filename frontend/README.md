# `frontend/` — Web application

**Purpose:** the user interface caregivers use. React + TypeScript, built with Vite.

- **Stack:** React, TypeScript, Vite, a router, and a lightweight data-fetching approach.
- **Contains (later phases):** pages (Dashboard, Residents, Care plans, Alerts), one typed
  API client in `src/api/`, shared UI components, and `vitest` tests.
- **Must NOT contain:** business logic, ML code, database access, or hard-coded URLs
  (use `VITE_API_BASE_URL` from `.env`).

**Status:** empty — not scaffolded yet (planned for milestone M3 in
[`../docs/roadmap.md`](../docs/roadmap.md)).

Commands that will be used later:
```bash
npm create vite@latest . -- --template react-ts   # scaffold (Phase 3)
npm install
npm run dev        # dev server on http://localhost:5173
npm run build      # production build
npm test           # vitest (Phase 8)
```
