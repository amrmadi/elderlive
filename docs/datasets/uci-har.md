# UCI HAR — Human Activity Recognition Using Smartphones

## 1. Source
- URL: https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones
- Publisher / authors: UCI Machine Learning Repository (originally: Reyes-Ortiz et al.,
  Universitat Politècnica de Catalunya) — verify citation on the UCI page
- Year: 2012 (verify on the UCI page)

## 2. License & allowed use
- License: UCI datasets of this era are commonly **CC BY 4.0** — **verify on the UCI page**
  and record the exact license text/link here before reuse
- Allowed for academic/project use?: Yes expected, confirm terms
- Attribution required: Yes — cite UCI ML Repository + original paper

## 3. Files
- File format: ZIP containing fixed-width text tables (`X_train.txt`, `y_train.txt`,
  `subject_train.txt`, …) plus a feature description file
- Approximate size: ~60 MB compressed (verify at download)
- Where stored locally (after download): `data/raw/uci-har/` (git-ignored)

## 4. Content & labels
- Signals / columns: tri-axial accelerometer + gyroscope captured at 50 Hz on a waist-mounted
  smartphone; 561 pre-computed features per window (verify against `features.txt`)
- Classes / labels (6): WALKING, WALKING_UPSTAIRS, WALKING_DOWNSTAIRS, SITTING, STANDING, LAYING
- Number of subjects / recordings: 30 volunteers (verify on the UCI page)

## 5. Preprocessing plan (draft)
- Step 1: the dataset is already windowed and feature-engineered — load provided train/test
  splits as a baseline
- Step 2: also record which subjects appear in which split; consider re-splitting by subject
  to check for leakage
- Step 3: standardize features using training statistics only
- Step 4: baseline model first (Logistic Regression or RandomForest), then optionally a
  1-D CNN on raw signals (raw time series are in the ZIP — verify)
- Step 5: report per-class precision/recall/F1, not just accuracy

## 6. Limitations & risks
- Healthy young adults, waist-mounted phone — not the same as elderly residents or wrist
  wearables; results will **not** directly transfer to real deployments
- Pre-computed features make it easy to report numbers that look great but teach us little —
  prefer also experimenting with raw signals
- 6 activities only — does not cover falls, so fall detection must come from UP-Fall
- Fixed, possibly leaky train/test split — re-check by subject

## 7. Status
- Downloaded: **no**
- Preprocessed: no
- Used for training: no
- Documented by: Phase 1 skeleton — confirm license + exact contents on the UCI page before
  download
