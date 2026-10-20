# UP-Fall Detection Dataset

## 1. Source
- URL: https://www.utdallas.edu/~kehtar/UP-Fall.html
- Publisher / authors: University of Texas at Dallas (Kehtar research group) — verify full author list on the page
- Year: To verify

## 2. License & allowed use
- License: **To verify** on the dataset page / accompanying publication before downloading
- Allowed for academic/project use?: To verify (commonly shared for research; confirm terms)
- Attribution required: To verify — cite the paper the page references

## 3. Files
- File format: To verify (expected: spreadsheet/CSV-style sensor tables plus labels)
- Approximate size: To verify at download time
- Where stored locally (after download): `data/raw/up-fall/` (git-ignored)

## 4. Content & labels
- Signals / columns: To verify — expected wearable/body sensor signals (accelerometer/gyro,
  possibly ECG/EMG/temperature) plus environmental sensors
- Classes / labels: To verify — expected: falls (multiple types) vs. ADL (activities of daily
  living) vs. no-data periods
- Number of subjects / recordings: To verify

## 5. Preprocessing plan (draft — refine after reading the documentation)
- Step 1: load sensor tables, align timestamps
- Step 2: clean missing values, apply units consistent with the documentation
- Step 3: window into fixed-size segments (e.g. 2–5 s, overlap 50%) — window size chosen
  after inspecting sampling rate
- Step 4: normalize features using training-set statistics only (no leakage)
- Step 5: stratified train/validation/test split **by subject**, not by row

## 6. Limitations & risks
- Recorded in a controlled lab setting — real homes are noisier
- Class imbalance (few falls compared with normal activity) — accuracy alone is misleading;
  report precision/recall/F1 for the fall class
- Subject-specific movement styles — splitting by row would inflate results (data leakage)
- Unknown until read: exact license, sampling rates, sensor placement

## 7. Status
- Downloaded: **no**
- Preprocessed: no
- Used for training: no
- Documented by: Phase 1 skeleton — fields marked "To verify" must be completed from the
  official page *before* download
