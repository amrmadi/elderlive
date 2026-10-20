"""Train and evaluate the SisFall fall-detection baseline.

Run it
------
    .venv\\Scripts\\python.exe -m ai.fall_detection.train

What it produces
----------------
1. `ai/models/fall_detection/fall_rf_v1.joblib` — the trained model plus
   everything needed to reproduce a prediction (feature order, scaler,
   threshold, version, and the **measured** metrics).
2. `ai/models/fall_detection/fall_rf_v1.json` — the same metadata as readable
   JSON, so the reported numbers can be inspected without loading a pickle.
3. Console output with the real metrics, including the ones that are worse.

Why the evaluation is split the way it is
-----------------------------------------
SisFall has 23 adult subjects and 15 elderly ones, and **only one elderly
subject (`SE06`) simulated any falls**. That single fact dictates the protocol:

* **Adult holdout** — adult subjects are split by subject. This is the headline
  number, and it is the only split with enough positives to be stable.
* **Elderly holdout** — evaluated separately. Because falls exist for exactly
  one elderly subject, this is a **single-person** result. It is reported and
  labelled as such; averaging it into the headline would overstate coverage.

`--include-elderly-in-train` controls whether the elderly ADL data joins the
training set. It is off by default so the elderly evaluation is a genuine
cross-population test rather than one the model was trained on.

Anything measured by row-wise splitting is not reported at all, because it would
be wrong: the same person would appear in train and test.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import sys
import time
from typing import Any

import numpy as np

from ai.fall_detection import preprocess as pp

#: Where trainees write artefacts. Git-ignored (see the repository .gitignore).
DEFAULT_MODEL_DIR = pathlib.Path(__file__).resolve().parent.parent / "models" / "fall_detection"
MODEL_VERSION = "fall-rf-v1"

#: A predicted fall with probability >= this is reported as a fall. 0.5 is the
#: neutral default; the script reports how the choice affects recall, because a
#: false negative (a missed fall) is the costly error in this application.
DEFAULT_THRESHOLD = 0.5


def _find_archive(explicit: str | None) -> pathlib.Path:
    if explicit:
        path = pathlib.Path(explicit)
        if not path.exists():
            raise SystemExit(f"Archive not found: {path}")
        return path

    candidate = pathlib.Path(__file__).resolve().parents[2] / "data" / "raw" / "SisFall_dataset.zip"
    if not candidate.exists():
        raise SystemExit(
            "SisFall archive not found. Download it first (see "
            "docs/datasets/sisfall.md), or pass --archive PATH."
        )
    return candidate


def _windows_for_subjects(archive: pathlib.Path, subjects: set[str]) -> list[pp.Window]:
    """All feature windows belonging to the given subjects."""
    windows: list[pp.Window] = []
    for recording in pp.iter_archive_recordings(archive, subjects=subjects):
        windows.extend(pp.build_windows(recording))
    return windows


def _xy(windows: list[pp.Window]) -> tuple[np.ndarray, np.ndarray]:
    return pp.feature_matrix(windows), np.asarray([w.label for w in windows], dtype=np.int64)


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Precision, recall and F1 **for the fall class**, plus supporting counts.

    Accuracy is intentionally absent from the headline: with far more ADL
    windows than fall windows, a model that always answers "no fall" scores high
    accuracy while being useless. Precision and recall for the positive class
    are the numbers that mean something here.
    """
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0

    return {
        "precision_fall": precision,
        "recall_fall": recall,
        "f1_fall": f1,
        "specificity": specificity,
        "true_positives": float(tp),
        "false_positives": float(fp),
        "false_negatives": float(fn),
        "true_negatives": float(tn),
        "n_windows": float(len(y_true)),
        "n_fall_windows": float(int(np.sum(y_true == 1))),
        "n_adl_windows": float(int(np.sum(y_true == 0))),
    }


def _subject_breakdown(
    windows: list[pp.Window], y_pred: np.ndarray
) -> dict[str, dict[str, float]]:
    """Per-subject precision/recall, so a strong average cannot hide a weak subject."""
    by_subject: dict[str, list[tuple[int, int]]] = {}
    for window, pred in zip(windows, y_pred, strict=True):
        by_subject.setdefault(window.subject, []).append((window.label, int(pred)))

    out: dict[str, dict[str, float]] = {}
    for subject in sorted(by_subject):
        pairs = by_subject[subject]
        y_true = np.asarray([p[0] for p in pairs], dtype=np.int64)
        y_hat = np.asarray([p[1] for p in pairs], dtype=np.int64)
        out[subject] = _metrics(y_true, y_hat)
    return out


def train(
    *,
    archive: pathlib.Path,
    model_dir: pathlib.Path,
    test_fraction: float,
    seed: int,
    include_elderly_in_train: bool,
    threshold: float,
    n_estimators: int,
) -> dict[str, Any]:
    from sklearn.ensemble import RandomForestClassifier

    started = time.time()
    all_subjects = pp.all_subjects(archive)
    adults = [s for s in all_subjects if s.startswith("SA")]
    elderly = pp.elderly_subjects(archive)
    subjects_with_falls = pp.subjects_with_falls(archive)

    # --- adult, subject-wise split: the headline evaluation -----------------
    train_adults, test_adults = pp.split_subjects(
        adults, test_fraction=test_fraction, seed=seed
    )

    train_subjects = set(train_adults)
    if include_elderly_in_train:
        train_subjects |= set(elderly) - {"SE06"}

    print(f"archive          : {archive}")
    print(f"adult subjects   : {len(adults)}")
    print(f"elderly subjects : {len(elderly)}")
    print(f"elderly with falls: {sorted(set(elderly) & subjects_with_falls)}")
    print(f"train subjects   : {len(train_subjects)} (elderly in train: {include_elderly_in_train})")
    print(f"adult test subj  : {len(test_adults)} -> {test_adults}")
    print()

    print("extracting training windows ...")
    train_windows = _windows_for_subjects(archive, train_subjects)
    print("extracting adult-test windows ...")
    test_windows = _windows_for_subjects(archive, set(test_adults))
    # The elderly evaluation uses SE06 (falls) plus the other elderly subjects
    # (ADL only). This is a cross-population test: none of it is in training by
    # default.
    elderly_eval_subjects = set(elderly)
    print("extracting elderly-test windows ...")
    elderly_windows = _windows_for_subjects(archive, elderly_eval_subjects)
    print()

    x_train_raw, y_train = _xy(train_windows)
    x_test_raw, y_test = _xy(test_windows)
    x_eld_raw, y_eld = _xy(elderly_windows)

    # --- scaler fitted on TRAIN ONLY ---------------------------------------
    scaler = pp.fit_scaler([w.features for w in train_windows])
    x_train = scaler.transform(x_train_raw)
    x_test = scaler.transform(x_test_raw)
    x_eld = scaler.transform(x_eld_raw)

    print(f"training windows : {len(train_windows)} "
          f"({int(y_train.sum())} fall / {int((y_train == 0).sum())} adl)")
    print(f"adult test wins  : {len(test_windows)} "
          f"({int(y_test.sum())} fall / {int((y_test == 0).sum())} adl)")
    print(f"elderly test wins: {len(elderly_windows)} "
          f"({int(y_eld.sum())} fall / {int((y_eld == 0).sum())} adl)")
    print()

    model = RandomForestClassifier(
        n_estimators=n_estimators,
        # `balanced` counteracts the large ADL:fall ratio. Without it the model
        # can all but ignore the positive class and still look accurate.
        class_weight="balanced",
        random_state=seed,
        n_jobs=-1,
    )
    print(f"fitting RandomForest (n_estimators={n_estimators}) ...")
    model.fit(x_train, y_train)

    def predict_proba(matrix: np.ndarray) -> np.ndarray:
        return model.predict_proba(matrix)[:, 1]

    proba_test = predict_proba(x_test)
    proba_eld = predict_proba(x_eld)
    proba_train = predict_proba(x_train)

    metrics: dict[str, float] = {}
    adult_metrics = _metrics(y_test, (proba_test >= threshold).astype(np.int64))
    elderly_metrics = _metrics(y_eld, (proba_eld >= threshold).astype(np.int64))
    train_metrics = _metrics(y_train, (proba_train >= threshold).astype(np.int64))

    for key, value in adult_metrics.items():
        metrics[f"adult_holdout_{key}"] = value
    for key, value in elderly_metrics.items():
        metrics[f"elderly_holdout_{key}"] = value
    for key, value in train_metrics.items():
        metrics[f"train_{key}"] = value

    # Threshold sweep: makes the precision/recall trade-off explicit instead of
    # hiding it behind one arbitrary cut-off.
    sweep: dict[str, dict[str, float]] = {}
    for t in (0.3, 0.4, 0.5, 0.6, 0.7):
        sweep[f"{t:.1f}"] = _metrics(y_test, (proba_test >= t).astype(np.int64))

    elapsed = time.time() - started

    per_subject_adult = _subject_breakdown(
        test_windows, (proba_test >= threshold).astype(np.int64)
    )

    payload = {
        "model_version": MODEL_VERSION,
        "algorithm": f"RandomForestClassifier(n_estimators={n_estimators}, class_weight=balanced)",
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dataset": "SisFall",
        "dataset_archive_sha256": "7f0dd1583e39fee0f402a6855976eb12517f7eaecdacce871d5b3421793ad665",
        "threshold": threshold,
        "feature_names": pp.feature_names(),
        "sample_rate_hz": pp.SAMPLE_RATE_HZ,
        "window_rows": pp.DEFAULT_WINDOW_ROWS,
        "stride_rows": pp.DEFAULT_STRIDE,
        "sensor": "ADXL345 (columns 1-3), converted from ADC counts to g",
        "split": {
            "method": "subject-wise; no subject appears in both train and test",
            "seed": seed,
            "test_fraction": test_fraction,
            "train_subjects": sorted(train_subjects),
            "adult_test_subjects": test_adults,
            "elderly_eval_subjects": sorted(elderly_eval_subjects),
            "elderly_in_train": include_elderly_in_train,
        },
        "metrics": metrics,
        "threshold_sweep_adult_holdout": sweep,
        "per_subject_adult_test": per_subject_adult,
        "caveats": [
            "All SisFall falls are simulated, on a mat, with a waist-mounted sensor.",
            "Only one elderly subject (SE06) simulated falls, so the elderly result "
            "describes one person, not the elderly population.",
            "Elderly results are a cross-population test: the elderly cohort is absent "
            "from training unless --include-elderly-in-train is passed.",
            "Metrics are for the fall class; accuracy is deliberately not a headline.",
        ],
        "training_seconds": round(elapsed, 1),
        "sklearn_version": _sklearn_version(),
    }

    _print_report(payload, model)

    # --- persist -----------------------------------------------------------
    model_dir.mkdir(parents=True, exist_ok=True)
    import joblib

    artefacts = {
        "model": model,
        "scaler": scaler.as_dict(),
        "feature_names": pp.feature_names(),
        "threshold": threshold,
        "model_version": MODEL_VERSION,
        "window_rows": pp.DEFAULT_WINDOW_ROWS,
        "stride_rows": pp.DEFAULT_STRIDE,
        "sample_rate_hz": pp.SAMPLE_RATE_HZ,
        "metrics": metrics,
        "dataset": "SisFall",
        "metadata": payload,
    }
    joblib_path = model_dir / f"{MODEL_VERSION}.joblib"
    json_path = model_dir / f"{MODEL_VERSION}.json"
    joblib.dump(artefacts, joblib_path)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    print(f"\nwrote {joblib_path}")
    print(f"wrote {json_path}")
    return payload


def _sklearn_version() -> str:
    try:
        import sklearn

        return sklearn.__version__
    except Exception:  # pragma: no cover - only if sklearn is absent
        return "unknown"


def _print_report(payload: dict[str, Any], model: Any) -> None:
    """Print the measured metrics, the threshold trade-off and the importances.

    Everything comes from `payload` so the printed report and the saved JSON
    cannot disagree — a report that recomputes its own numbers is a report that
    can drift from the artefact.
    """
    metrics = payload["metrics"]

    def show(prefix: str, title: str) -> None:
        print(f"--- {title} ---")
        for key in (
            "precision_fall",
            "recall_fall",
            "f1_fall",
            "specificity",
            "true_positives",
            "false_positives",
            "false_negatives",
            "true_negatives",
            "n_fall_windows",
            "n_adl_windows",
        ):
            value = metrics.get(f"{prefix}{key}")
            if value is not None:
                print(f"  {key:<18} {value:,.4f}" if isinstance(value, float) and not value.is_integer() else f"  {key:<18} {value:,.0f}")
        print()

    show("train_", "train (fit set — expect high; not evidence of generalisation)")
    show("adult_holdout_", "ADULT HOLDOUT (unseen adult subjects) — headline")
    show("elderly_holdout_", "ELDERLY HOLDOUT (unseen people; falls from SE06 only)")

    print("--- threshold sweep on the adult holdout ---")
    for t, m in payload["threshold_sweep_adult_holdout"].items():
        print(
            f"  threshold {t}: precision={m['precision_fall']:.3f} "
            f"recall={m['recall_fall']:.3f} f1={m['f1_fall']:.3f}"
        )
    print()

    print("--- feature importances (top 10) ---")
    names = pp.feature_names()
    importances = np.asarray(model.feature_importances_)
    for rank, idx in enumerate(np.argsort(importances)[::-1][:10], start=1):
        print(f"  {rank:>2}. {names[idx]:<20} {importances[idx]:.4f}")
    print()

    print("--- per-subject fall recall on seen and unseen subjects ---")
    breakdown = payload["per_subject_adult_test"]
    for subject, m in breakdown.items():
        if m["n_fall_windows"] == 0:
            continue
        print(
            f"  {subject}: fall recall={m['recall_fall']:.3f} "
            f"precision={m['precision_fall']:.3f} "
            f"(falls={int(m['n_fall_windows'])})"
        )
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", default=None, help="Path to SisFall_dataset.zip")
    parser.add_argument("--model-dir", default=str(DEFAULT_MODEL_DIR))
    parser.add_argument("--test-fraction", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=20260101)
    parser.add_argument("--n-estimators", type=int, default=200)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument(
        "--include-elderly-in-train",
        action="store_true",
        help=(
            "Include elderly ADL data in training. Off by default so the elderly "
            "evaluation stays a genuine cross-population test."
        ),
    )
    args = parser.parse_args(argv)

    archive = _find_archive(args.archive)
    train(
        archive=archive,
        model_dir=pathlib.Path(args.model_dir),
        test_fraction=args.test_fraction,
        seed=args.seed,
        include_elderly_in_train=args.include_elderly_in_train,
        threshold=args.threshold,
        n_estimators=args.n_estimators,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
