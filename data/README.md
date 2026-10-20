# `data/` — Datasets

**Purpose:** local storage for research data. **Almost everything here is git-ignored** —
datasets are large and have their own licenses.

| Subfolder | What lives there | Git status |
|---|---|---|
| `raw/` | Original downloaded files (UP-Fall, CASAS, UCI HAR). **Never edit these.** | ignored |
| `processed/` | Cleaned/encoded data produced by preprocessing scripts | ignored |
| `sample/` | Tiny hand-made example files used by tests (a few KB) | allowed |

**Rules**
1. Download datasets **by hand** into `raw/` — no scripts that download automatically.
2. Document each dataset in [`../docs/datasets/`](../docs/datasets/README.md) *before* download.
3. Preprocessing always goes `raw/` → (script) → `processed/`, so raw data stays pristine.
4. Never put real personal data of real people here. Only public research datasets or
   clearly-synthetic test records.

**Status:** empty — no dataset has been downloaded (by design, Phase 1 rule).
