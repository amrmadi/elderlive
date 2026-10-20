# `ai/fall_detection/` — Fall detection

**Goal:** decide whether a short window of sensor data represents a fall.

- **Planned dataset:** UP-Fall (see [`../../docs/datasets/up-fall.md`](../../docs/datasets/up-fall.md))
- **Planned approach:** start simple — windowed features + RandomForest baseline; only try a
  deep model if the baseline is clearly insufficient
- **Expected output:** `FallDetectionResult { is_fall, confidence, model_version, occurred_at }`

**Status:** empty. Nothing implemented, nothing trained. (Milestone M6.)
