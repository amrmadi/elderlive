# `ai/activity_recognition/` — Activity recognition

**Goal:** classify a time window of motion data into an activity label
(e.g. walking, sitting, lying).

- **Planned dataset:** UCI HAR
- **Planned approach:** logistic-regression / RandomForest baseline on the
  provided features, optionally a 1-D CNN on raw signals later
- **Expected output:** `ActivityResult { label, confidence, model_version }`

**Status:** declared only. Nothing implemented, nothing trained, and no model is
shipped in this repository. The registry returns `is_ready: false` for this
problem, so the API reports it as unavailable rather than guessing.

See [`../base.py`](../base.py) for the `ActivityResult` type and
[`../registry.py`](../registry.py) for how the backend asks for this predictor.
