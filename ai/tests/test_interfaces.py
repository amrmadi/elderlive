"""Tests for the AI inference interfaces in `ai/base.py` and `ai/registry.py`.

These run with **no dataset, no trained model, and no network access**, which
is the whole point of keeping the interfaces dependency-free.

The tests check three kinds of thing:

* the types behave correctly (validation, serialisation, the ambiguity check);
* the honesty rules cannot be bypassed (simulated data is always flagged;
  an unready predictor never invents an answer);
* the "no model" story is told consistently, so the API cannot accidentally
  present placeholders as real predictions.
"""

from __future__ import annotations

import pytest

from ai.base import (
    ActivityResult,
    AnomalyResult,
    FallDetectionResult,
    ModelInfo,
    ModelNotLoadedError,
    Predictor,
)
from ai.registry import AVAILABLE_PREDICTORS, get_predictor, list_predictors


# ---------------------------------------------------------------------------
# FallDetectionResult
# ---------------------------------------------------------------------------


def test_fall_result_round_trips_through_as_dict() -> None:
    result = FallDetectionResult(
        model_version="fall-rf-v1",
        is_fall=True,
        confidence=0.87,
        explanation="Vertical acceleration spike followed by 4s of inactivity.",
        source="sensor",
    )

    payload = result.as_dict()

    assert payload["is_fall"] is True
    assert payload["confidence"] == 0.87
    assert payload["model_version"] == "fall-rf-v1"
    assert payload["kind"] == "fall_detection"
    assert payload["is_simulated"] is False


def test_fall_result_rejects_confidence_outside_zero_to_one() -> None:
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        FallDetectionResult(model_version="m", confidence=1.5)

    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        FallDetectionResult(model_version="m", confidence=-0.1)


def test_fall_result_requires_a_model_version() -> None:
    """A result that cannot name its model cannot be audited."""
    with pytest.raises(ValueError, match="model_version must be set"):
        FallDetectionResult(model_version="")


def test_a_positive_fall_prediction_always_needs_human_review() -> None:
    positive = FallDetectionResult(model_version="m", is_fall=True, confidence=0.99)
    negative = FallDetectionResult(model_version="m", is_fall=False, confidence=0.01)

    assert positive.needs_human_review is True
    assert negative.needs_human_review is False


def test_simulated_fall_data_is_flagged_as_not_a_real_measurement() -> None:
    """The core honesty rule: demo input must never look like a real reading."""
    demo = FallDetectionResult(model_version="m", source="simulated")
    research = FallDetectionResult(model_version="m", source="imported_dataset")
    live = FallDetectionResult(model_version="m", source="sensor")

    assert demo.is_simulated is True
    assert research.is_simulated is True
    assert live.is_simulated is False


def test_results_are_immutable() -> None:
    """A prediction is a record of what the model said; it must not be edited."""
    result = FallDetectionResult(model_version="m", is_fall=True, confidence=0.9)
    with pytest.raises(Exception):
        result.is_fall = False  # type: ignore[misc]


def test_details_defaults_are_not_shared_between_instances() -> None:
    """A mutable default would leak state across results — a classic bug."""
    first = FallDetectionResult(model_version="m")
    second = FallDetectionResult(model_version="m")

    first.details["threshold"] = 0.6

    assert second.details == {}


# ---------------------------------------------------------------------------
# ActivityResult
# ---------------------------------------------------------------------------


def test_activity_result_carries_the_whole_distribution() -> None:
    result = ActivityResult(
        model_version="har-rf-v1",
        activity="walking",
        confidence=0.62,
        scores={"walking": 0.62, "standing": 0.30, "sitting": 0.08},
        source="sensor",
    )

    assert result.activity == "walking"
    assert result.scores["standing"] == 0.30
    assert result.kind == "activity_recognition"


def test_activity_result_rejects_an_out_of_range_score() -> None:
    with pytest.raises(ValueError, match="score for 'walking'"):
        ActivityResult(model_version="m", scores={"walking": 1.4})


def test_close_top_two_activities_are_reported_as_ambiguous() -> None:
    """62 % vs 55 % is not a confident label, and must not be presented as one."""
    ambiguous = ActivityResult(
        model_version="m",
        activity="walking",
        confidence=0.62,
        scores={"walking": 0.62, "standing": 0.55},
    )
    clear = ActivityResult(
        model_version="m",
        activity="walking",
        confidence=0.95,
        scores={"walking": 0.95, "standing": 0.03},
    )

    assert ambiguous.is_ambiguous is True
    assert clear.is_ambiguous is False


def test_activity_without_a_distribution_is_not_claimed_ambiguous() -> None:
    """With no distribution we cannot tell, so we must not guess either way."""
    result = ActivityResult(model_version="m", activity="walking", confidence=0.7)
    assert result.is_ambiguous is False


# ---------------------------------------------------------------------------
# AnomalyResult
# ---------------------------------------------------------------------------


def test_anomaly_result_records_direction_and_features() -> None:
    result = AnomalyResult(
        model_version="routine-iforest-v1",
        is_anomaly=True,
        deviation_score=3.4,
        direction="below",
        deviating_features={"kitchen_visits": -2.1, "night_wakeups": 1.4},
        explanation="Far fewer kitchen visits than this person's usual day.",
    )

    assert result.direction == "below"
    assert result.deviating_features["kitchen_visits"] == -2.1
    assert result.kind == "anomaly_detection"


def test_anomaly_result_rejects_features_without_a_direction() -> None:
    """Explaining what moved without saying which way is self-contradictory."""
    with pytest.raises(ValueError, match="direction is 'none'"):
        AnomalyResult(
            model_version="m",
            is_anomaly=True,
            deviating_features={"kitchen_visits": -2.1},
        )


def test_anomaly_result_is_not_a_diagnosis() -> None:
    """The serialised payload must not contain medical-risk language."""
    result = AnomalyResult(model_version="m", is_anomaly=True, deviation_score=3.0)
    payload = result.as_dict()

    assert "diagnosis" not in payload
    assert "risk" not in payload
    assert payload["is_anomaly"] is True


# ---------------------------------------------------------------------------
# ModelNotLoadedError
# ---------------------------------------------------------------------------


def test_model_not_loaded_error_names_the_model_and_explains_itself() -> None:
    error = ModelNotLoadedError("fall_detection")

    assert error.model_name == "fall_detection"
    assert "not loaded" in str(error)
    assert error.reason


def test_model_not_loaded_error_accepts_a_specific_reason() -> None:
    error = ModelNotLoadedError("activity_recognition", reason="Model file missing.")
    assert "Model file missing." in str(error)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_declares_all_three_problems() -> None:
    assert set(AVAILABLE_PREDICTORS) == {
        "fall_detection",
        "activity_recognition",
        "anomaly_detection",
    }


def test_no_predictor_is_ready_today() -> None:
    """No model has been trained, so nothing may claim to be ready."""
    for name in AVAILABLE_PREDICTORS:
        assert get_predictor(name).is_ready() is False


def test_predicting_without_a_model_raises_rather_than_guessing() -> None:
    for name in AVAILABLE_PREDICTORS:
        with pytest.raises(ModelNotLoadedError):
            get_predictor(name).predict(features=[1.0, 2.0, 3.0])


def test_unavailable_predictor_reports_no_metrics() -> None:
    """Metrics must be None, never fabricated numbers."""
    for name in AVAILABLE_PREDICTORS:
        info = get_predictor(name).info
        assert info.metrics is None
        assert info.trained_at is None
        assert info.version == ""


def test_unavailable_predictor_still_names_its_planned_dataset() -> None:
    """Provenance is stated even before training, so it cannot be forgotten later."""
    assert get_predictor("fall_detection").info.dataset == "SisFall"
    assert get_predictor("activity_recognition").info.dataset == "UCI HAR"
    assert get_predictor("anomaly_detection").info.dataset == "CASAS"


def test_unknown_predictor_name_fails_loudly() -> None:
    """A typo must not silently return a placeholder."""
    with pytest.raises(KeyError, match="Unknown predictor"):
        get_predictor("fortune_telling")


def test_predictors_satisfy_the_protocol() -> None:
    """The placeholders must be usable wherever a real predictor is expected."""
    for name in AVAILABLE_PREDICTORS:
        assert isinstance(get_predictor(name), Predictor)


def test_list_predictors_summarises_every_problem() -> None:
    described = list_predictors()

    assert len(described) == 3
    assert {entry["name"] for entry in described} == set(AVAILABLE_PREDICTORS)
    # Every entry must admit it is not ready and has no measured metrics.
    assert all(entry["is_ready"] is False for entry in described)
    assert all(entry["metrics"] is None for entry in described)
    assert all(entry["model_version"] is None for entry in described)


def test_model_info_metrics_default_to_none() -> None:
    info = ModelInfo(name="x", version="1", kind="fall_detection")
    assert info.metrics is None
    assert info.trained_at is None
