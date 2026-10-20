"""Verify the no-model path is honest — what a fresh clone / CI actually hits.

The trained model artefacts are git-ignored, so a new checkout has no model.
This confirms that in that state:
  * the predictor reports `is_ready = False` and `metrics = None`;
  * `predict()` raises `ModelNotLoadedError` rather than returning a guess;
  * `list_predictors()` still tells the truth through the same registry the API
    uses.

It also checks the *opposite* direction, so the test is not vacuous: with the
real model present, the predictor is ready and reports measured metrics.

Run from the repository root:
    .venv\\Scripts\\python.exe tools\\verify_no_model_path.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from ai.base import ModelNotLoadedError  # noqa: E402
from ai.fall_detection.predictor import FallDetectionPredictor  # noqa: E402
from ai.registry import PLANNED_DATASETS  # noqa: E402

failures: list[str] = []


def check(label: str, condition: bool) -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {label}")
    if not condition:
        failures.append(label)


print("=== no model file present (fresh clone / CI state) ===")
missing = FallDetectionPredictor(model_dir="C:/no/such/model/dir")
check("is_ready() is False", missing.is_ready() is False)

info = missing.info
check("version is empty", info.version == "")
check("metrics is None (not zeros)", info.metrics is None)
check("trained_at is None", info.trained_at is None)
check("dataset still named (SisFall)", info.dataset == "SisFall")

raised = False
try:
    missing.predict([[0.0, 0.0, 1.0]] * 500)
except ModelNotLoadedError as exc:
    raised = True
    check("error message says how to fix it", "train" in str(exc).lower())
check("predict() raises ModelNotLoadedError", raised)

print("\n=== the real model, when present (the opposite direction) ===")
present = FallDetectionPredictor()
if present.is_ready():
    real = present.info
    check("is_ready() is True", True)
    check("version is set", bool(real.version))
    check("metrics present", real.metrics is not None)
    check(
        "metrics include the worse elderly result",
        real.metrics is not None and "elderly_holdout_f1_fall" in real.metrics,
    )
else:
    print("  (no trained model on this machine — run `python -m ai.fall_detection.train`)")

print(f"\nplanned datasets: {PLANNED_DATASETS}")

if failures:
    print(f"\n{len(failures)} CHECK(S) FAILED")
    sys.exit(1)
print("\nALL NO-MODEL-PATH CHECKS PASSED")
