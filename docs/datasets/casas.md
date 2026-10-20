# CASAS Smart Home Datasets

## 1. Source
- URL: http://casas.wsu.edu/datasets/
- Publisher / authors: Washington State University, CASAS smart-home project
- Year: continuous releases — pick the specific dataset set at download time and record it here

## 2. License & allowed use
- License: **To verify** on the datasets page (research-use terms expected — confirm)
- Allowed for academic/project use?: To verify
- Attribution required: To verify — cite the CASAS project/publications

## 3. Files
- File format: To verify (expected: plain-text event logs — timestamp, sensor id, sensor value)
- Approximate size: To verify — individual sets are usually small-to-medium text files
- Where stored locally (after download): `data/raw/casas/` (git-ignored)

## 4. Content & labels
- Signals / columns: To verify — expected: ambient sensor events (door, motion, temperature,
  bed/chair pressure, etc.) as timestamped discrete events
- Classes / labels: To verify — expected: annotated activities of daily living and/or
  scripted errors depending on the chosen set
- Number of subjects / recordings: To verify (homes vary: apartments, houses, testbeds)

## 5. Preprocessing plan (draft — refine after reading the documentation)
- Step 1: parse event logs into (timestamp, sensor, value) tuples
- Step 2: discretize continuous values; build time-binned activity sequences per hour/block
- Step 3: define "normal routine" features per resident: activity counts, time-of-day
  distributions, room usage, intervals between events
- Step 4: hold out a time period as an "evaluation" window for anomaly scoring
- Step 5: keep labels (if any) only for evaluation — anomaly detection will be mostly
  unsupervised, so be explicit about what is actually measurable

## 6. Limitations & risks
- Activity annotations differ between CASAS sets — not all sets have labels
- Sensor layouts differ between homes; a model tuned to one home may not transfer
- Unsupervised anomaly detection has no ground truth in some sets — be honest about how
  "anomaly quality" will be evaluated (e.g. does it flag scripted errors when present?)
- Never record real elderly residents' behavior in this project — CASAS is simulated/scripted

## 7. Status
- Downloaded: **no**
- Preprocessed: no
- Used for training: no
- Documented by: Phase 1 skeleton — record the exact set name + license before downloading
