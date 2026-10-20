# SisFall: A Fall and Movement Dataset

> **Why this file exists and why it replaces UP-Fall.** The original plan named
> UP-Fall for fall detection. On inspection its full distribution is ~812 GB,
> which is not practical to download or process for this project. SisFall is the
> standard alternative for the same problem and is ~221 MB. UP-Fall is therefore
> **not used**, and [`up-fall.md`](up-fall.md) is retained only as a record of
> the decision. Every field below was verified against the archive actually
> downloaded, not copied from a summary.

## 1. Source

- URL: <https://www.mdpi.com/1424-8220/17/1/198> (paper)
- Original host: `http://sistemic.udea.edu.co/.../english-falls/` —
  **verified unreachable** on 2026-10-20 (`Unable to connect to the remote server`).
  The link is widely reported as broken, and the authors' contact details are in
  the paper.
- Mirror actually used:
  <https://huggingface.co/datasets/Algo-rythmic/Sisfall_Dataset>
  (a re-host of the original archive under the dataset's own CC BY 4.0 licence)
- Publisher / authors: Sucerquia, A.; López, J. D.; Vargas-Bonilla, J. F.
  — SISTEMIC, Faculty of Engineering, Universidad de Antioquia (UDEA), Colombia
- Year: 2017 (paper); dataset version 1.0, February 2016
- Citation:
  Sucerquia A, López JD, Vargas-Bonilla JF. *SisFall: A Fall and Movement
  Dataset.* Sensors. 2017; 17(1):198.

## 2. License & allowed use

- License: **CC BY 4.0** as stated on the mirror's own page
  (`"re-hosted here under the Creative Commons Attribution 4.0 International
  (CC BY 4.0) license"`)
- Allowed for academic/project use?: Yes — the paper states the dataset is
  "available for free download as Supplementary Materials"
- Attribution required: **Yes.** Credit the original authors and cite the 2017
  Sensors paper. This repository does not redistribute the data; it is
  git-ignored and downloaded on demand.

## 3. Files

- Archive: `SisFall_dataset.zip`
- Size: **232,407,821 bytes** (221.6 MiB)
- SHA-256 of the downloaded zip:
  `7f0dd1583e39fee0f402a6855976eb12517f7eaecdacce871d5b3421793ad665`
  (the mirror's ETag is a different value — an ETag is not a content hash, so the
  archive was verified with `zipfile.testzip()` instead, which passed)
- Contents: **9,484 members** = 4,742 real entries + 4,742 macOS `__MACOSX`
  metadata entries. Only `SisFall_dataset/**` is used; `__MACOSX` is ignored.
- Data files: **4,505** recordings, plus the shipped `Readme.txt` (**4,506** `.txt`
  members in total). The Readme states 4,510 recordings; this re-host is missing a
  small number, most likely some of `SE06`'s fall trials — see §6
- File format: plain text. Nine comma-separated integer columns per row, each row
  terminated with `;`. Rows vary per recording.
- Where stored locally: `data/raw/SisFall_dataset.zip` (git-ignored); extracted
  working data under `data/processed/` (git-ignored)

## 4. Content & labels

Verified from `SisFall_dataset/Readme.txt` inside the archive and by counting the
members:

- **Subjects: 38** — `SA01`–`SA23` (adults aged 19–30) and `SE01`–`SE15`
  (elderly, aged 60–75).
- **19 ADL codes** `D01`–`D19` and **15 fall codes** `F01`–`F15`.
- Filename format: `<CODE>_<SUBJECT>_R<TRIAL>.txt`, e.g. `F05_SA01_R04.txt`.
- Repetitions: `R01`–`R06` (most activities have 5 trials).
- Sampling rate: **200 Hz**.
- Columns:
  1–3 `ADXL345` acceleration X, Y, Z — 13-bit, ±16 g
  4–6 `ITG3200` rotation X, Y, Z — 16-bit, ±2000 °/s
  7–9 `MMA8451Q` acceleration X, Y, Z — 14-bit, ±8 g
- Values are **raw ADC bits**, not physical units. The Readme gives:
  - Acceleration [g] = `(2 × Range) / (2^Resolution) × AD`
  - Angular velocity [°/s] = `(2 × Range) / (2^Resolution) × RD`
- Labels: `D…` = activity of daily living (negative class), `F…` = fall
  (positive class).

Selected activities, quoted from the Readme:

| Code | Activity |
|---|---|
| `D01` | Walking slowly |
| `D02` | Walking quickly |
| `D11` | Sitting a moment, trying to get up, and collapse into a chair |
| `D18` | Stumble while walking |
| `D19` | Gently jump without falling (trying to reach a high object) |
| `F04` | Fall forward while walking caused by a trip |
| `F06` | Vertical fall while walking caused by fainting |

`D11`, `D18` and `D19` are deliberately kept as **negatives**: they are the hard
cases that a naive "big acceleration = fall" rule gets wrong.

## 5. Preprocessing plan

Implemented in `ai/fall_detection/preprocess.py`.

1. **Parse** nine integer columns, strip the trailing `;`, drop rows that are not
   nine integers.
2. **Convert to physical units** using the Readme's formulas. Work from the
   `ADXL345` triplet (columns 1–3) because the paper itself uses that sensor.
3. **Window**: sliding window over each recording. Falls are 15 s and ADLs 12–100 s
   at 200 Hz, so windows must be short enough to localise a fall. Window and
   stride are recorded with the processed output.
4. **Feature extraction** per window: time-domain statistics plus magnitude-based
   features that are orientation-tolerant.
5. **Split by subject, never by row.** Windows from one person must not appear in
   both train and test, or the score is meaningless.
6. **Fit scalers on the training split only**, then apply to validation/test.

## 6. Limitations & risks

- **Only one elderly subject (`SE06`) simulated falls.** This was checked file by
  file against the archive: `SE06` has 75 fall recordings, and the other fourteen
  elderly subjects (`SE01`–`SE05`, `SE07`–`SE15`) have **none**. The paper says
  the same. The practical consequence is unavoidable: an elderly test split has
  **no positive class beyond a single person**, so a single-subject elderly score
  reflects one individual, not "the elderly". It is reported because it is the
  honest number, and it is labelled as single-subject rather than generalised.
- **The paper's claim that elderly participants skipped `D06`, `D13`, `D18`, `D19`
  does not hold for this archive.** The paper describes the original collection;
  in the re-host actually downloaded, every elderly subject has the same 15–19
  ADL codes as the adults (verified by counting per subject). The paper's
  statement is therefore recorded here as a claim we **could not reproduce**, not
  as a property of the data in use.
  A model trained on the adults' data and tested on the elderly is the honest
  test, and the paper itself reports that performance **drops significantly** on
  elderly subjects. This must be reported, not hidden.
- **All falls are simulated**, performed by volunteers on a mat, not real falls.
  They are not real-world fall data.
- Waist-mounted sensor, controlled lab setting; a real home deployment would be
  noisier and differently worn.
- **Class imbalance**: 15 fall types × 5 trials × mostly adult subjects, against a
  much larger ADL set. **Accuracy is therefore misleading**; precision, recall and
  F1 for the *fall* class are reported instead.
- **Subject-specific movement styles**: splitting by row would inflate results.
- The re-host is missing a few files relative to the Readme's stated 4,510
  (4,505 recordings present). Recorded here rather than quietly ignored.
- This is **public research data recorded from other people.** It is never stored
  as, or presented as, an ElderLife resident's own reading.

## 7. Status

- Downloaded: **yes** — 2026-10-20, 232,407,821 bytes, zip integrity verified
- Preprocessed: yes — see `data/processed/fall_detection/` (git-ignored) and
  `ai/fall_detection/preprocess.py`
- Used for training: yes — see `ai/fall_detection/`; metrics are reported in
  `ai/fall_detection/README.md` **as measured**, including the subject-split
  results where they are worse
- Documented by: Phase 5 (AI), against the archive itself
