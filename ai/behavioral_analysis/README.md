# `ai/behavioral_analysis/` — Behavioural anomaly detection

**Goal:** learn each resident's normal routine and flag unusual patterns
(e.g. not leaving bed at the usual time, wandering at night).

- **Planned dataset:** CASAS smart-home logs
- **Planned approach:** per-resident routine baselines (time-of-day activity
  distributions) plus an unsupervised detector such as IsolationForest, or simple
  statistical thresholds
- **Expected output:** `AnomalyResult { is_anomalous, score, model_version }`

**Honesty note:** unsupervised anomaly detection is hard to evaluate. Any future
work here must state exactly how "it works" was measured — and what could **not**
be measured. Do not report an accuracy figure that was not measured.

**Status:** declared only. Nothing implemented, nothing trained, and no model is
shipped in this repository. The registry returns `is_ready: false` for this
problem, so the API reports it as unavailable rather than guessing.

See [`../base.py`](../base.py) for the `AnomalyResult` type and
[`../registry.py`](../registry.py) for how the backend asks for this predictor.
