# Dataset documentation

> Rule: **document a dataset here BEFORE downloading or using it.** Nothing in `data/` is
> committed to Git. One dataset (SisFall) has been downloaded and used for training; the
> others have not.

## The template

Copy the template below into a new file (e.g. `up-fall.md`) and fill in every field.
Unknown information is written as `To verify` — never guessed.

```markdown
# <Dataset name>

## 1. Source
- URL:
- Publisher / authors:
- Year:

## 2. License & allowed use
- License:
- Allowed for academic/project use?:
- Attribution required:

## 3. Files
- File format:
- Approximate size:
- Where stored locally (after download):

## 4. Content & labels
- Signals / columns:
- Classes / labels:
- Number of subjects / recordings:

## 5. Preprocessing plan
- Steps (windowing, cleaning, normalization, train/test split):

## 6. Limitations & risks
- Known biases / constraints:
- Things this dataset cannot prove:

## 7. Status
- Downloaded: no
- Preprocessed: no
- Used for training: no
- Documented by / date:
```

## Dataset index

| # | Dataset | Used for | Page | Status |
|---|---|---|---|---|
| 1 | **SisFall** | fall detection | [sisfall.md](sisfall.md) | ✅ **downloaded, preprocessed, trained** |
| 2 | CASAS Smart Home | behavioral anomaly detection | [casas.md](casas.md) | not downloaded |
| 3 | UCI HAR (Smartphones) | activity recognition | [uci-har.md](uci-har.md) | not downloaded |
| 4 | UP-Fall Detection Dataset | *(superseded by SisFall)* | [up-fall.md](up-fall.md) | not used — ~812 GB |

## Rules for working with datasets

1. Download **manually** into `data/raw/` (git-ignored) — never commit raw data.
2. Keep raw files untouched; write scripts that produce `data/processed/`.
3. Never use real personal data about actual elderly people in this project.
4. Record license terms before using data in a public demo or paper.
5. Because these are research datasets, remember: good results on them do **not**
   guarantee real-world accuracy. This limitation must appear in the final thesis.
