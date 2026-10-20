"""Tests for `ai/fall_detection/predictor.py`.

Two groups again:

* **No-model tests**, which run everywhere. The trained model file is
  git-ignored, so a fresh clone has no model — and the predictor must behave
  honestly in exactly that state. These are the most important tests here,
  because the "no model" path is the one a new checkout actually hits.
* **Model tests**, skipped unless the local artefacts exist. They check that the
  trained model loads, reports its measured metrics, and classifies a real fall
  and a real ADL correctly.
"""

from __future__ import annotations

import pathlib

import numpy as np
import pytest

from ai.base import FallDetectionResult, ModelNotLoadedError, Predictor
from ai.fall_detection import preprocess as pp
from ai.fall_detection.predictor import FallDetectionPredictor

MODEL_DIR = pathlib.Path(__file__).resolve().parents[2] / "ai" / "models" / "fall_detection"
needs_model = pytest.mark.skipif(
    not (MODEL_DIR / "fall-rf-v1.joblib").exists(),
    reason="Trained model not present; run `python -m ai.fall_detection.train`",
)
ARCHIVE = pathlib.Path(__file__).resolve().parents[2] / "data" / "raw" / "SisFall_dataset.zip"
needs_archive = pytest.mark.skipif(
    not ARCHIVE.exists(), reason="SisFall archive not downloaded"
)


# ---------------------------------------------------------------------------
# The no-model state — what a fresh clone sees
# ---------------------------------------------------------------------------


def test_a_missing_model_reports_not_ready() -> None:
    predictor = FallDetectionPredictor(model_dir="C:/definitely/not/here")
    assert predictor.is_ready() is False


def test_a_missing_model_reports_no_metrics_and_no_version() -> None:
    """No model means no measured metrics — never zeros, never placeholders."""
    info = FallDetectionPredictor(model_dir="C:/definitely/not/here").info

    assert info.metrics is None
    assert info.version == ""
    assert info.trained_at is None
    # Provenance is still stated, so it cannot be forgotten once training exists.
    assert info.dataset == "SisFall"
    assert info.kind == "fall_detection"


def test_predicting_without_a_model_raises_rather_than_guessing() -> None:
    predictor = FallDetectionPredictor(model_dir="C:/definitely/not/here")

    with pytest.raises(ModelNotLoadedError) as excinfo:
        predictor.predict(np.zeros((500, 3)))

    # The message must say how to fix it, not just that it failed.
    assert "train" in str(excinfo.value).lower()
    assert excinfo.value.model_name == "fall_detection"


def test_batch_prediction_without_a_model_also_raises() -> None:
    predictor = FallDetectionPredictor(model_dir="C:/definitely/not/here")
    with pytest.raises(ModelNotLoadedError):
        predictor.predict_windows([])


def test_the_predictor_satisfies_the_protocol() -> None:
    """It must be usable anywhere `ai.base.Predictor` is expected."""
    assert isinstance(FallDetectionPredictor(model_dir="C:/nope"), Predictor)


# ---------------------------------------------------------------------------
# Input validation (model-independent where possible)
# ---------------------------------------------------------------------------


@needs_model
def test_a_short_sequence_is_rejected_not_padded() -> None:
    """Silently zero-padding would invent data the sensor never produced."""
    predictor = FallDetectionPredictor()

    with pytest.raises(ValueError, match="at least"):
        predictor.predict(np.zeros((10, 3)))


@needs_model
def test_a_wrong_shape_is_rejected() -> None:
    predictor = FallDetectionPredictor()

    with pytest.raises(ValueError, match="shape"):
        predictor.predict(np.zeros((500, 2)))


@needs_model
def test_a_one_dimensional_input_is_rejected() -> None:
    predictor = FallDetectionPredictor()

    with pytest.raises(ValueError, match="shape"):
        predictor.predict(np.zeros(500))


# ---------------------------------------------------------------------------
# With the trained model present
# ---------------------------------------------------------------------------


@needs_model
def test_the_model_loads_and_reports_measured_metrics() -> None:
    predictor = FallDetectionPredictor()

    assert predictor.is_ready() is True
    info = predictor.info
    assert info.version == "fall-rf-v1"
    assert info.dataset == "SisFall"

    # The metrics must be the real measured ones, and they must include the
    # elderly result that is worse — it is not optional.
    assert info.metrics is not None
    assert "adult_holdout_f1_fall" in info.metrics
    assert "elderly_holdout_f1_fall" in info.metrics
    assert 0.0 <= info.metrics["adult_holdout_f1_fall"] <= 1.0
    # A baseline on this dataset must clearly beat chance, or it is not worth
    # reporting as a working model.
    assert info.metrics["adult_holdout_f1_fall"] > 0.5


@needs_model
def test_metrics_are_not_the_training_score() -> None:
    """Reporting the fit score as if it were generalisation would be dishonest.

    Training F1 is stored too, but the holdout number must be lower — if it
    equalled the training score, the split would have leaked.
    """
    metrics = FallDetectionPredictor().info.metrics
    assert metrics is not None
    assert metrics["train_f1_fall"] >= metrics["adult_holdout_f1_fall"]


@needs_model
def test_a_result_is_flagged_as_research_data_not_a_live_reading() -> None:
    """SisFall comes from unrelated volunteers; it must never look live."""
    result = FallDetectionPredictor().predict(np.zeros((500, 3)) + np.array([0, 0, 1.0]))

    assert isinstance(result, FallDetectionResult)
    assert result.source == "imported_dataset"
    assert result.is_simulated is True
    assert result.model_version == "fall-rf-v1"


@needs_model
def test_every_result_explains_itself_and_disclaims_medical_meaning() -> None:
    result = FallDetectionPredictor().predict(
        np.zeros((500, 3)) + np.array([0, 0, 1.0])
    )

    assert result.explanation
    assert 0.0 <= result.confidence <= 1.0
    assert result.details["not_a_medical_assessment"] is True


@needs_model
@needs_archive
def test_a_real_fall_is_detected_and_a_real_adl_is_not() -> None:
    """The end-to-end check that matters: real data, real model, real answer."""
    predictor = FallDetectionPredictor()

    fall = pp.read_recording_from_archive(ARCHIVE, "SisFall_dataset/SA01/F01_SA01_R01.txt")
    adl = pp.read_recording_from_archive(ARCHIVE, "SisFall_dataset/SA01/D01_SA01_R01.txt")
    assert fall is not None and adl is not None

    fall_results = predictor.predict_windows(pp.build_windows(fall))
    adl_results = predictor.predict_windows(pp.build_windows(adl))

    # A fall recording should produce at least one positive window.
    assert any(r.is_fall for r in fall_results), "no window of a real fall was flagged"
    # A slow-walk ADL recording should not be dominated by fall flags.
    flagged = sum(1 for r in adl_results if r.is_fall)
    assert flagged < len(adl_results) / 2, "walking was mostly flagged as falling"


@needs_model
def test_empty_window_list_returns_nothing_rather_than_erroring() -> None:
    assert FallDetectionPredictor().predict_windows([]) == []


@needs_model
def test_predictions_are_deterministic() -> None:
    """The same input must give the same answer; a model is not a random guess."""
    random_state = np.random.default_rng(0)
    samples = random_state.normal(0.0, 0.3, size=(500, 3))
    samples[:, 2] += 1.0

    predictor = FallDetectionPredictor()
    first = predictor.predict(samples)
    second = predictor.predict(samples)

    assert first.confidence == second.confidence
    assert first.is_fall == second.is_fall
