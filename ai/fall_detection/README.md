# `ai/fall_detection/` — Fall detection

**Goal:** decide whether a short window of accelerometer data represents a fall.

## Status: implemented and trained

This is the one AI problem in the project with a real, trained model behind it.
Everything below is measured, and the numbers that are *worse* are reported
alongside the ones that flatter the model.

```
python -m ai.fall_detection.train      # retrains and rewrites the artefacts
```

| Piece | File |
|---|---|
| Preprocessing, windowing, features, subject split | [`preprocess.py`](preprocess.py) |
| Training + evaluation | [`train.py`](train.py) |
| Serving predictor (loads the model) | [`predictor.py`](predictor.py) |

- **Dataset:** SisFall — see [`../../docs/datasets/sisfall.md`](../../docs/datasets/sisfall.md).
  (The original plan named UP-Fall, whose full distribution is ~812 GB and was
  not practical. SisFall is the standard alternative at ~221 MB.)
- **Approach:** windowed time-domain features + `RandomForestClassifier`, as the
  plan specified. A deep model is only worth trying if this baseline proves
  insufficient — and it has not needed to.
- **Output:** `FallDetectionResult { is_fall, confidence, model_version, occurred_at }`
  via `predictor.py`.

## How a prediction is produced

1. **Parse** the nine integer columns, strip the trailing `;`, keep rows with
   exactly nine integers.
2. **Convert** the first three columns (`ADXL345`) from raw ADC counts to g:
   `g = (2 × 16) / 2¹³ × AD`. Columns 1–3 are the sensor the SisFall paper itself
   analyses.
3. **Window** each recording into **2.0 s** windows (400 rows at 200 Hz) with a
   **1.0 s** stride (50 % overlap). A fall recording is 15 s and an ADL recording
   is 10–180 s, so windows localise a fall inside a long file.
4. **Extract 40 features**: 10 statistics × 4 signals. The four signals are the
   three axes plus the **vector magnitude**, which does not change when the
   device is rotated on the body — the main difference between a lab recording
   and a real deployment.
5. **Classify** with the trained forest at a 0.50 threshold.

## Evaluation protocol (and why it is shaped this way)

The single most important property is that **the split is by subject, never by
row**. Windows from one person must not appear in both train and test, or the
model is graded on people it has memorised.

Two evaluations are reported:

- **Adult holdout** — 6 of the 23 adult subjects, held out entirely. This is the
  headline number, and the only one with enough falls to be stable.
- **Elderly holdout** — all 15 elderly subjects, kept out of training by default.

### A fact that constrains the elderly result

Only **one** elderly subject (`SE06`) simulated any falls. The other fourteen
have **none**. So the elderly evaluation is, unavoidably, a **single-person**
result: it says how the model behaves on one elderly volunteer, not on "the
elderly". It is reported because it is the honest number, and labelled so it is
not over-read.

The paper reports that performance drops significantly on elderly subjects. The
measurements here reproduce that.

## Measured results

Trained with `RandomForestClassifier(n_estimators=200, class_weight=balanced)`,
`random_state=20260101`, on the archive with SHA-256
`7f0dd158…93ad665`. Reproduce with `python -m ai.fall_detection.train`.

### Adult holdout (6 unseen adult subjects) — headline

| Metric | Value |
|---|---|
| **Precision (fall)** | **0.812** |
| **Recall (fall)** | **0.795** |
| **F1 (fall)** | **0.804** |
| Specificity | 0.863 |
| Fall windows | 6,267 |
| ADL windows | 8,450 |

Per-subject fall recall on the six unseen adults ranged from **0.742** to
**0.852** — no single subject was carried by the average.

### Elderly holdout (unseen people; falls from SE06 only)

| Metric | Value |
|---|---|
| Precision (fall) | 0.201 |
| Recall (fall) | 0.845 |
| F1 (fall) | 0.325 |
| Specificity | 0.796 |

Recall stays high but **precision collapses**: the model fires often on elderly
ADL. This is the cross-population gap, and it is the reason the model is framed
as a prompt for human review rather than an alarm.

### Threshold behaviour (adult holdout)

The operating threshold is a policy choice, so the trade-off is published rather
than hidden:

| Threshold | Precision | Recall | F1 |
|---|---|---|---|
| 0.3 | 0.669 | **0.913** | 0.772 |
| 0.4 | 0.738 | 0.855 | 0.792 |
| **0.5** | **0.812** | 0.795 | **0.804** |
| 0.6 | 0.878 | 0.732 | 0.799 |
| 0.7 | **0.918** | 0.668 | 0.773 |

In a care setting a missed fall is usually the costlier error, which argues for a
lower threshold — at the price of more false alarms. The default is 0.5; the data
to choose otherwise is above.

**Accuracy is deliberately not a headline number.** There are far more ADL
windows than fall windows, so a model that always answers "no fall" scores well
while being useless. The reported metric is `train_f1_fall = 1.000` — the fit
score, which is *not* evidence of generalisation and is stored only so a leak
would be visible if the holdout score ever matched it.

## What the model is not

- Every SisFall fall was **simulated**, on a mat, with a waist-mounted sensor.
  These are not real falls, and the data is from unrelated volunteers — results
  are always marked `source="imported_dataset"`, so `is_simulated` is `True` and
  the UI is forced to label them as research data rather than a resident reading.
- A positive prediction **requires human verification**. `needs_human_review` is
  `True` for any positive, and the result carries
  `not_a_medical_assessment: True`. Operational triage is not a medical risk
  assessment.
- The elderly number rests on one person, as explained above.
- The model sees a 2 s window at 200 Hz from one waist sensor. A real home
  deployment would be noisier and differently worn.

## Artefacts

Written to `ai/models/fall_detection/` (git-ignored):

- `fall-rf-v1.joblib` — model, scaler, feature order, threshold, measured metrics.
- `fall-rf-v1.json` — the same metadata as readable JSON, so the numbers can be
  inspected without unpickling.

Because the model is git-ignored, a fresh clone must run the training command
before the API reports `is_ready: true`. Until then the predictor reports no
metrics and the API returns an honest **503 `MODEL_NOT_LOADED`** — verified in
[`../../tools/verify_no_model_path.py`](../../tools/verify_no_model_path.py).
