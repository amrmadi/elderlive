# `ai/` — Typed AI interfaces

**Purpose:** the shared, typed interfaces the backend depends on. This is a
plain Python package that the backend imports, which keeps AI result types
testable without a server or a database.

> **This folder is a backend dependency, not AI work.** The backend's AI router
> does `from ai.base import ...`, so the API cannot start without this package.
> Model training and the trained model files are **not part of this
> repository** — see [Not in this repository](../README.md#not-in-this-repository).

## What is here

| File | Contents |
|---|---|
| [`base.py`](base.py) | The typed result classes (`FallDetectionResult`, `ActivityResult`, `AnomalyResult`), `ModelInfo`, the `Predictor` protocol, and `ModelNotLoadedError` |
| [`registry.py`](registry.py) | Looks up a predictor by name; reports whether each is usable |
| `activity_recognition/`, `behavioral_analysis/` | Placeholder folders documenting the declared problems |

## What is *not* here

- **No trained model.** `ai/models/` is git-ignored and empty in a fresh clone.
- **No training code.** Preprocessing and training scripts are out of scope for
  this repository.
- **No datasets.** Public research data is never committed.

Because no model is shipped, **every** predictor reports `is_ready: false` and
calling one raises `ModelNotLoadedError`, which the API turns into an honest
**HTTP 503 `MODEL_NOT_LOADED`** rather than a plausible-looking guess.

```python
>>> from ai.registry import list_predictors
>>> [(p["name"], p["is_ready"], p["metrics"]) for p in list_predictors()]
[('fall_detection', False, None),
 ('activity_recognition', False, None),
 ('anomaly_detection', False, None)]
```

`metrics` is `None`, never zeros or placeholders — fabricated evaluation numbers
would be worse than no numbers.

## The three declared problems

| Problem | Dataset it would use | Status here |
|---|---|---|
| Fall detection | SisFall | Declared, **no model shipped** |
| Activity recognition | UCI HAR | Declared, no model |
| Behavioural anomaly detection | CASAS | Declared, no model |

The dataset names are recorded in `registry.py` so the API can state its intended
provenance without reading documentation at runtime.

## The contract

Every predictor implements the `Predictor` protocol in [`base.py`](base.py) and
returns one of the typed results. Two honesty rules are enforced by the types
themselves:

1. A result derived from `simulated` or `imported_dataset` input is flagged
   `is_simulated=True`, so public research data can never be presented as a
   resident's own reading.
2. A predictor with no model raises `ModelNotLoadedError`, which the API turns
   into **503 `MODEL_NOT_LOADED`** rather than a guess.

## How the backend uses it

`backend/app/api/routers/ai.py` exposes:

- `GET /api/v1/ai/predictors` — the capability list
- `GET /api/v1/ai/predictors/{name}` — one predictor's metadata
- `POST /api/v1/ai/predictors/{name}/check` — run a prediction (returns `503`
  here, because no model is shipped)

These are covered by `backend/tests/test_ai_api.py`, which asserts that the
endpoint never fabricates a label.
