# `ai/` — Machine learning code

**Purpose:** the three AI problems of the project, kept as a plain Python package that the
backend imports. Keeping AI separate makes models testable without a server or database.

| Subfolder | Problem | Dataset | Status |
|---|---|---|---|
| [`fall_detection/`](fall_detection/) | Is this a fall? | **SisFall** | ✅ **trained** — F1 0.80 on unseen adults |
| [`activity_recognition/`](activity_recognition/) | What activity is happening? | UCI HAR | Declared, no model |
| [`behavioral_analysis/`](behavioral_analysis/) | Is today's routine unusual? | CASAS | Declared, no model |

The dataset column reflects what each problem is actually trained on. Fall detection uses
SisFall rather than the originally-planned UP-Fall, whose full distribution is ~812 GB and
was not practical; see [`../docs/datasets/sisfall.md`](../docs/datasets/sisfall.md).

**Shared rules for all AI subfolders:**
1. Pure functions: data in → prediction out. No HTTP, no database calls inside.
2. Training scripts write model files to `ai/models/` (git-ignored). No model is committed,
   so a fresh clone must train before the API reports a predictor as ready.
3. Every model records version + metrics; results carry `.model_version`.
4. Tests run without network access or downloaded datasets for the pure logic; tests that
   need the archive or the model are skipped automatically when those are absent.
5. Nothing is trained until its dataset is downloaded **and** documented in
   [`../docs/datasets/`](../docs/datasets/README.md).

## The contract

Every predictor implements the `Predictor` protocol in [`base.py`](base.py) and returns one
of the typed results. Two honesty rules are enforced by the types themselves:

1. A result derived from `simulated` or `imported_dataset` input is flagged
   `is_simulated=True`, so public research data can never be presented as a resident's own
   reading.
2. A predictor with no model raises `ModelNotLoadedError`, which the API turns into an
   honest **503 `MODEL_NOT_LOADED`** rather than a plausible-looking guess.

[`registry.py`](registry.py) is how the backend asks for a predictor by name. Today
`fall_detection` returns a real predictor; the other two return a placeholder that refuses
to predict.

## Tests

```
.venv\Scripts\python.exe -m pytest ai\tests -q
```

`test_interfaces.py` covers the shared types and the honesty rules; `test_preprocess.py`
covers parsing, the subject-wise split and the train-only scaler rule;
`test_fall_predictor.py` covers both the no-model and trained-model paths.

## Status

Phase 5 (AI) is under way: fall detection is implemented and trained. Activity recognition
and behavioural analysis remain declared-but-untrained (milestones M6 and M7).
