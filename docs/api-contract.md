# ElderLife AI — API Contract

> Status: **proposed contract** (Phase 1). No endpoint exists yet. This document is the
> agreement between the frontend, the backend, and the AI modules so that all three can be
> built independently and still fit together. If the contract must change, update this file
> in the same pull request as the code.

---

## 1. Conventions

| Topic | Rule |
|---|---|
| Base URL | `http://localhost:8000/api/v1` (path-versioned; `v1` never changes meaning) |
| Format | `application/json; charset=utf-8` (except exports, which are CSV/Parquet) |
| Timestamps | ISO 8601 in UTC, e.g. `2026-10-20T18:30:00Z` |
| IDs | Integers, assigned by the database |
| Pagination | `?page=1&page_size=50` → response includes `items`, `total`, `page`, `page_size` |
| Success | Any 2xx with the resource (or `{ "items": [...] }` for lists) |
| Errors | Every 4xx/5xx returns the same envelope (below) |

### Error envelope

```json
{
  "error": {
    "code": "RESIDENT_NOT_FOUND",
    "message": "Resident with id 42 does not exist.",
    "details": null
  }
}
```

`code` is a stable machine string (frontend may branch on it); `message` is human-readable.

### Common status codes

`200` OK · `201 Created` · `204 No Content` · `400` bad input · `401` not authenticated
(future) · `403` forbidden (future) · `404` not found · `409` conflict · `422` validation
error · `500` server error.

---

## 2. REST endpoints (planned)

### 2.1 System

| Method | Path | Purpose | Phase |
|---|---|---|---|
| GET | `/health` | Liveness + DB connectivity check | 2 |

```json
// GET /api/v1/health → 200
{ "status": "ok", "database": "connected", "version": "0.1.0" }
```

### 2.2 Residents

| Method | Path | Purpose | Phase |
|---|---|---|---|
| GET | `/residents` | List residents (paginated) | 2 |
| POST | `/residents` | Create a resident | 2 |
| GET | `/residents/{id}` | One resident | 2 |
| PATCH | `/residents/{id}` | Partial update | 2 |
| DELETE | `/residents/{id}` | Remove (soft-delete preferred) | 2 |

```json
// POST /api/v1/residents → 201
{
  "id": 1,
  "first_name": "example",
  "last_name": "resident",
  "date_of_birth": "1948-04-12",
  "room": "A-101",
  "is_active": true,
  "created_at": "2026-10-20T18:30:00Z"
}
```

> Only care-related fields. **Never** store national IDs, medical record numbers, or other
> sensitive personal data in this project.

### 2.3 Care plans

| Method | Path | Purpose | Phase |
|---|---|---|---|
| GET | `/residents/{id}/care-plans` | Plans for one resident | 4 |
| POST | `/residents/{id}/care-plans` | Create a plan (goals, schedule, notes) | 4 |
| PATCH | `/care-plans/{id}` | Update a plan | 4 |
| POST | `/care-plans/{id}/tasks/{task_id}/complete` | Mark a scheduled task done | 4 |

### 2.4 Sensor data & events

| Method | Path | Purpose | Phase |
|---|---|---|---|
| POST | `/sensor-data` | Ingest one reading/frame from a device or simulator | 2 / 6 |
| GET | `/residents/{id}/readings` | Readings over a time range | 3 |
| GET | `/events` | Detected events (falls, activities, anomalies) | 6 |

```json
// POST /api/v1/sensor-data → 202 (accepted for processing)
{
  "resident_id": 1,
  "device_id": "sim-01",
  "captured_at": "2026-10-20T18:30:00Z",
  "reading_type": "accelerometer",
  "values": { "x": 0.12, "y": 0.98, "z": 0.04 }
}
```

### 2.5 AI inference (exposed by the backend)

| Method | Path | Purpose | Phase |
|---|---|---|---|
| GET | `/ai/models` | Which models are loaded, their status/version | 6 |
| POST | `/ai/fall-detection` | Run fall detection on a frame/segment | 6 |
| POST | `/ai/activity-recognition` | Classify an activity segment | 6 |
| POST | `/ai/behavior-check` | Compare recent routine with the resident baseline | 6 |

```json
// POST /api/v1/ai/fall-detection → 200
{
  "is_fall": true,
  "confidence": 0.91,
  "model_version": "fall_rf_0001",
  "occurred_at": "2026-10-20T18:30:00Z"
}
```

> Until Phase 6 completes, these endpoints return `503` with code `MODEL_NOT_LOADED`.
> **We will not fake predictions.**

### 2.6 Alerts

| Method | Path | Purpose | Phase |
|---|---|---|---|
| GET | `/alerts` | List alerts (filter: status, severity, resident) | 5 |
| POST | `/alerts/{id}/acknowledge` | Caregiver confirms an alert | 5 |
| WS | `/ws/alerts` | Real-time alert push | 5 |

```json
// Alert object
{
  "id": 10,
  "resident_id": 1,
  "alert_type": "fall",
  "severity": "critical",
  "confidence": 0.91,
  "status": "new",
  "message": "Possible fall detected for resident 1.",
  "created_at": "2026-10-20T18:30:00Z",
  "acknowledged_at": null
}
```

### 2.7 Analytics

| Method | Path | Purpose | Phase |
|---|---|---|---|
| GET | `/analytics/summary` | Counts & trends for the dashboard | 7 |
| GET | `/analytics/export?format=csv` | CSV/Parquet download for Power BI | 7 |

---

## 3. Contract between backend and AI modules (in-process Python)

The backend does **not** call the AI code over HTTP — it imports it as a package.
The AI layer must stay pure: *data in → result out*, no database or HTTP inside.

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

### Input shapes

- `FallFrame` — timestamp, device id, and either raw sensor values (accelerometer/gyro) or
  pre-extracted features, depending on the model.
- `ActivitySegment` — a time window of readings plus sampling rate.
- `ActivityEvent` — a stored history entry (activity label, start/end time, resident id).

### Rules for AI modules

1. No `print()` debugging — use the standard `logging` module.
2. Every model file records its version and training date.
3. Missing model file ⇒ raise `ModelNotLoadedError` ⇒ backend answers `503 MODEL_NOT_LOADED`.
4. Unit tests must run without a database or network.

---

## 4. Frontend ↔ backend rules

- All requests go through one typed API client (`frontend/src/api/`), no scattered `fetch` calls.
- The frontend reads `VITE_API_BASE_URL` from `.env` — URLs are never hard-coded.
- The frontend displays only what the API returns; it never invents readings or alerts.
- Loading, empty, and error states are always handled (an empty dashboard must not look broken).

---

## 5. Versioning & change process

1. Additive changes (new fields/endpoints) do not bump the version.
2. Breaking changes get a new prefix (`/api/v2`) and a note in this document.
3. This file and the code change together — it is the source of truth for integration.
