# `ai/behavioral_analysis/` — Behavioral anomaly detection

**Goal:** learn each resident's normal routine and flag unusual patterns
(e.g. not leaving bed at the usual time, wandering at night).

- **Planned dataset:** CASAS smart-home logs (see [`../../docs/datasets/casas.md`](../../docs/datasets/casas.md))
- **Planned approach:** per-resident routine baselines (time-of-day activity distributions)
  + an unsupervised detector such as IsolationForest or simple statistical thresholds
- **Expected output:** `AnomalyResult { is_anomalous, score, model_version }`

**Honesty note:** unsupervised anomaly detection is hard to evaluate. The final report must
state exactly how "it works" was measured — and what could not be measured.

**Status:** empty. Nothing implemented, nothing trained. (Milestone M6.)
