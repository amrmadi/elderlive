# `ai/activity_recognition/` — Activity recognition

**Goal:** classify a time window of motion data into an activity label
(e.g. walking, sitting, lying).

- **Planned dataset:** UCI HAR (see [`../../docs/datasets/uci-har.md`](../../docs/datasets/uci-har.md))
- **Planned approach:** logistic-regression / RandomForest baseline on the provided features,
  optionally a 1-D CNN on raw signals later
- **Expected output:** `ActivityResult { label, confidence, model_version }`

**Status:** empty. Nothing implemented, nothing trained. (Milestone M6.)
