# ElderLife AI — API Contract

> **Status: implemented (Phase 3).** Every endpoint marked ✅ below exists in the code
> and is covered by the test suite in `backend/tests/`. Sections marked 🔜 are *planned*
> for a later phase and **do not exist yet** — the frontend must not call them.
>
> This document is the agreement between the frontend, the backend, and the AI modules.
> If the contract changes, update this file in the same commit as the code.

---

## 0. Where to see the live contract

The backend generates its own OpenAPI documentation, which is always in sync with the code:

| URL | What it shows |
|---|---|
| `http://localhost:8000/docs` | Interactive Swagger UI — you can call endpoints from the browser |
| `http://localhost:8000/redoc` | Readable API reference |
| `http://localhost:8000/openapi.json` | The raw OpenAPI 3.1 schema the frontend types are generated from |

The tables below describe *why* each endpoint exists. When the two disagree, **the generated
OpenAPI schema is authoritative** because it comes from the running code.

---

## 1. Conventions

| Topic | Rule |
|---|---|
| Base URL | `http://localhost:8000/api/v1` (path-versioned; `v1` never changes meaning) |
| Health at root | `GET /health` also exists without the `/api/v1` prefix, for Docker and load-balancer probes |
| Format | `application/json; charset=utf-8` |
| Timestamps | ISO 8601 in UTC, e.g. `2026-10-20T18:30:00Z` |
| Dates | `YYYY-MM-DD`, e.g. `1948-04-12` |
| Times | 24-hour `HH:MM`, e.g. `08:30` |
| IDs | Integers, assigned by the database |
| Pagination | `?page=1&page_size=50` → response has `items`, `total`, `page`, `page_size` |
| Auth | `Authorization: Bearer <access_token>` on every endpoint except register/login/health |

### Error envelope

Every 4xx/5xx response has the **same** shape, so the frontend needs only one error path:

```json
{
  "error": {
    "code": "ELDERLY_PROFILE_NOT_FOUND",
    "message": "Resident with id 42 does not exist.",
    "details": null
  }
}
```

`code` is a stable machine string the frontend may branch on. `message` is safe to show to a user.
For validation failures, `details` names the offending fields:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "One or more fields were invalid. See details for specifics.",
    "details": { "fields": [ { "field": "display_name", "message": "Display name cannot be blank.", "type": "value_error" } ] }
  }
}
```

### Status codes actually returned

`200` OK · `201` Created · `401` not authenticated / bad credentials · `403` forbidden
(you are not assigned to this resident, or your role does not permit it) · `404` not found ·
`409` conflict (duplicate email, duplicate assignment, already-closed alert) ·
`422` validation error · `500` server error · `503` dependency unavailable.

---

## 2. Implemented endpoints (Phase 3) ✅

### 2.1 System

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Liveness + **real** DB connectivity check |
| GET | `/health` | Same, without the version prefix (for Docker healthchecks) |
| GET | `/api/v1/version` | Version + environment name, no DB access |

```json
// GET /api/v1/health → 200
{ "status": "ok", "database": "connected", "version": "0.1.0", "environment": "development" }
```

> When the database is unreachable this reports `"database": "disconnected"` and
> `"status": "degraded"` rather than falsely claiming everything is fine.

### 2.2 Authentication

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/auth/register` | Create a **caregiver** or **elderly** account → `201` + token |
| POST | `/api/v1/auth/login` | Exchange email + password for a token |
| GET | `/api/v1/auth/me` | The signed-in user |

```json
// POST /api/v1/auth/login → 200
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": 1, "email": "caregiver@example.com", "display_name": "Example Caregiver",
    "phone": null, "role": "caregiver", "status": "active",
    "is_active": true, "is_email_verified": false,
    "created_at": "2026-10-20T18:30:00Z", "last_login_at": "2026-10-20T18:31:00Z"
  }
}
```

**Security rules encoded here:**
- Passwords are stored as Argon2 hashes; `password_hash` is **never** returned by any endpoint.
- Self-registration cannot create an `admin` or `analyst` — only `caregiver` or `elderly`.
- A wrong password and a non-existent email return the **identical** `401 INVALID_CREDENTIALS`,
  so the endpoint cannot be used to discover which emails are registered.

### 2.3 Elderly profiles

> Named "elderly profiles" in the code and API. The resident's `display_name` is a label, not
> necessarily a legal name. **Never** store national IDs, medical record numbers, or home
> addresses in this project.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/elderly-profiles` | List residents **you may access** (paginated) |
| POST | `/api/v1/elderly-profiles` | Create a resident; the creator is auto-assigned as primary caregiver |
| GET | `/api/v1/elderly-profiles/{profile_id}` | One resident |
| PATCH | `/api/v1/elderly-profiles/{profile_id}` | Partial update |
| DELETE | `/api/v1/elderly-profiles/{profile_id}` | **Soft delete** — sets `is_active=false`, never removes the row |

```json
// GET /api/v1/elderly-profiles/{id} → 200
{
  "id": 1, "display_name": "Margaret Example", "date_of_birth": "1948-04-12",
  "room_label": "A-101", "notes": "Prefers tea in the morning.",
  "mobility_notes": "Uses a walking frame", "linked_user_id": null,
  "is_active": true,
  "created_at": "2026-10-20T18:30:00Z", "updated_at": "2026-10-20T18:30:00Z"
}
```

List query parameters: `page`, `page_size` (max 200), `include_inactive` (default `false`).

### 2.4 Caregiver assignments

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/elderly-profiles/{profile_id}/caregivers` | Who is assigned to this resident |
| POST | `/api/v1/elderly-profiles/{profile_id}/caregivers` | Assign a caregiver |
| PATCH | `/api/v1/caregiver-assignments/{assignment_id}` | Change role, or deactivate to **revoke access** |

```json
// POST /api/v1/elderly-profiles/1/caregivers → 201
{
  "id": 5, "caregiver_id": 2, "elderly_profile_id": 1,
  "assignment_role": "secondary", "is_active": true,
  "assigned_at": "2026-10-20T18:30:00Z", "ended_at": null,
  "caregiver_display_name": "Second Caregiver", "caregiver_email": "second@example.com"
}
```

### 2.5 Care plans

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/elderly-profiles/{profile_id}/care-plans` | Plans for one resident (paginated) |
| POST | `/api/v1/elderly-profiles/{profile_id}/care-plans` | Create a plan |
| GET | `/api/v1/care-plans/{plan_id}` | One plan |
| PATCH | `/api/v1/care-plans/{plan_id}` | Partial update |
| DELETE | `/api/v1/care-plans/{plan_id}` | Delete a plan and its items |

### 2.6 Medication schedules

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/elderly-profiles/{profile_id}/medications` | What should be taken and when |
| POST | `/api/v1/elderly-profiles/{profile_id}/medications` | Create a schedule |

> The system **does not give medical advice**. `dosage_text` and `instructions` are free text
> entered by a caregiver; the API stores and returns them, nothing more.

### 2.7 Reminders

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/elderly-profiles/{profile_id}/reminders` | Repeating reminders (hydration, walks, …) |
| POST | `/api/v1/elderly-profiles/{profile_id}/reminders` | Create a reminder |

A `weekly` reminder **must** include `day_of_week` (1 = Monday … 7 = Sunday); the API rejects it
otherwise, because a weekly reminder with no weekday is ambiguous.

### 2.8 Check-ins

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/elderly-profiles/{profile_id}/checkins` | Check-in history (paginated, newest first) |
| POST | `/api/v1/elderly-profiles/{profile_id}/checkins` | Record an actual check-in |
| POST | `/api/v1/elderly-profiles/{profile_id}/checkin-schedules` | Define how often a check-in is expected |

`wellbeing_note` is free text, **not** a clinical score — the system does not diagnose.
A check-in with `status: "taken"` and no `performed_at` defaults to the current time.

### 2.9 Activity events

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/elderly-profiles/{profile_id}/activity-events` | Recorded activity history (paginated) |
| POST | `/api/v1/elderly-profiles/{profile_id}/activity-events` | Record an activity event |

Time filters are named `start` and `end` (ISO 8601), **not** `from`/`to`:

```
GET /api/v1/elderly-profiles/1/activity-events?start=2026-10-19T00:00:00Z&end=2026-10-20T00:00:00Z
```

> **Honesty guarantee.** Every activity event carries a `source` field which defaults to
> **`"simulated"`**. Demo or seeded data can therefore never be mistaken for a real sensor
> reading. Use `"sensor"` only for genuine device data, or `"model"` when a model produced it.

### 2.10 Alerts

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/alerts` | Alerts across every resident you can access (filters: `status`, `severity`) |
| GET | `/api/v1/elderly-profiles/{profile_id}/alerts` | Alerts for one resident |
| POST | `/api/v1/elderly-profiles/{profile_id}/alerts` | Raise an alert by hand |
| GET | `/api/v1/alerts/{alert_id}` | One alert |
| PATCH | `/api/v1/alerts/{alert_id}` | Change status or message |
| POST | `/api/v1/alerts/{alert_id}/acknowledge` | Caregiver confirms; records **who** and **when** |

```json
// Alert object
{
  "id": 10, "elderly_profile_id": 1, "alert_type": "fall", "severity": "critical",
  "status": "new", "title": "Possible fall", "message": "Reported by caregiver.",
  "source_event_type": null, "source_event_id": null, "occurrence_count": 1,
  "created_at": "2026-10-20T18:30:00Z",
  "acknowledged_at": null, "acknowledged_by_user_id": null, "resolved_at": null,
  "elderly_profile_name": "Margaret Example"
}
```

Statuses: `new` → `acknowledged` → `resolved` (or `dismissed`). A resolved or dismissed alert
cannot be acknowledged again (`409 ALERT_ALREADY_CLOSED`).

---

## 3. Access control (enforced on the server) 🔒

The frontend may hide buttons, but hidden buttons are **not** security — anyone can call the API
directly. Every rule here is checked again in the backend, regardless of what the UI shows.

| Role | May do |
|---|---|
| `admin` | Everything, including every resident's records |
| `caregiver` | Only residents they are **actively assigned** to; may create new residents (auto-assigned as primary) |
| `elderly` | Their own linked profile only |
| `analyst` | **No** individual care records — aggregates only (Phase 7) |

| Situation | Result |
|---|---|
| Resident does not exist | `404 ELDERLY_PROFILE_NOT_FOUND` |
| Resident exists but you are not assigned | `403 PERMISSION_DENIED` |
| Assignment exists but `is_active = false` | `403` — access follows the active flag, not the row's existence |
| Secondary caregiver tries to manage assignments | `403` — only `admin` or the **primary** caregiver |
| No assignments at all → list endpoints | Empty page, **never** everybody's residents |

---

## 4. Not implemented yet 🔜 (do not call these)

These appear in earlier drafts and in the architecture diagram. They **do not exist** and return
`404`. The frontend must not call them, and no page may pretend they work.

| Method | Path | Phase | Note |
|---|---|---|---|
| POST | `/sensor-data` | 6 | Raw sensor ingestion |
| GET | `/ai/models` | 6 | Which AI models are loaded |
| POST | `/ai/fall-detection` | 6 | Fall detection inference |
| POST | `/ai/activity-recognition` | 6 | Activity classification |
| POST | `/ai/behavior-check` | 6 | Routine anomaly check |
| GET | `/analytics/summary` | 7 | Dashboard aggregates |
| GET | `/analytics/export` | 7 | CSV/Parquet export for Power BI |
| WS | `/ws/alerts` | 5 | Real-time alert push |

> **We will not fake predictions.** Until Phase 6, there are deliberately no AI endpoints.
> When they are added, a missing model file will return `503 MODEL_NOT_LOADED` rather than a
> made-up answer.

---

## 5. Contract between backend and AI modules (in-process Python) 🔜

The backend does **not** call the AI code over HTTP — it imports it as a package. The AI layer
must stay pure: *data in → result out*, no database or HTTP inside.

```python
# ai/fall_detection/api.py  (planned signatures — not implemented yet)
def detect_fall(frame: FallFrame) -> FallDetectionResult: ...

# ai/activity_recognition/api.py
def classify_activity(segment: ActivitySegment) -> ActivityResult: ...

# ai/behavioral_analysis/api.py
def build_baseline(resident_id: int, history: list[ActivityEvent]) -> Baseline: ...
def check_anomaly(recent: list[ActivityEvent], baseline: Baseline) -> AnomalyResult: ...
```

### Shared result shapes

| Field | Type | Notes |
|---|---|---|
| `FallDetectionResult.is_fall` | bool | predicted class |
| `FallDetectionResult.confidence` | float 0–1 | model confidence |
| `ActivityResult.label` | str | e.g. `walking`, `lying`, `sitting` |
| `ActivityResult.confidence` | float 0–1 | model confidence |
| `AnomalyResult.is_anomalous` | bool | deviation from personal baseline |
| `AnomalyResult.score` | float ≥ 0 | higher = more unusual |
| all results `.model_version` | str | for traceability in the database |

### Rules for AI modules

1. No `print()` debugging — use the standard `logging` module.
2. Every model file records its version and training date.
3. Missing model file ⇒ raise `ModelNotLoadedError` ⇒ backend answers `503 MODEL_NOT_LOADED`.
4. Unit tests must run without a database or network.
5. Public research datasets (UP-Fall, CASAS, UCI HAR) stay separate from application user
   records — they are training data, never mixed into the operational database.

---

## 6. Frontend ↔ backend rules

- All requests go through one typed API client (`frontend/src/api/`), no scattered `fetch` calls.
- The frontend reads `VITE_API_BASE_URL` from `.env` — URLs are never hard-coded.
- The frontend displays only what the API returns; it never invents readings or alerts.
- Loading, empty, and error states are always handled (an empty dashboard must not look broken).
- Any demo/seeded data is labelled as such in the UI.

---

## 7. Versioning & change process

1. Additive changes (new fields/endpoints) do not bump the version.
2. Breaking changes get a new prefix (`/api/v2`) and a note in this document.
3. This file and the code change together — it is the source of truth for integration.
