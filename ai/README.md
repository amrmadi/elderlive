# `ai/` — Machine learning code

**Purpose:** the three AI problems of the project, kept as a plain Python package that the
backend imports. Keeping AI separate makes models testable without a server or database.

| Subfolder | Problem | Dataset (planned) |
|---|---|---|
| [`fall_detection/`](fall_detection/) | Is this a fall? | UP-Fall |
| [`activity_recognition/`](activity_recognition/) | What activity is happening? | UCI HAR |
| [`behavioral_analysis/`](behavioral_analysis/) | Is today's routine unusual? | CASAS |

**Shared rules for all AI subfolders:**
1. Pure functions: data in → prediction out. No HTTP, no database calls inside.
2. Training scripts write model files to `ai/models/` (git-ignored).
3. Every model records version + metrics; results carry `.model_version`.
4. Tests run without network access or downloaded datasets.
5. Nothing is trained until its dataset is downloaded **and** documented in
   [`../docs/datasets/`](../docs/datasets/README.md).

**Status:** empty — no code, no models, no training (milestone M6).
