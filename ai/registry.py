"""Registry of the AI predictors the backend can ask for.

Right now **every** predictor in this registry is a placeholder that has no
model behind it. Their only job is to report that honestly:

    >>> from ai.registry import get_predictor
    >>> predictor = get_predictor("fall_detection")
    >>> predictor.is_ready()
    False

The value of writing them now is that the backend, the API schema, and the
tests can all be built against the real contract. When Phase 5 produces a
trained model, `UnavailablePredictor` is replaced by a real class that loads it
— and nothing else has to change.
"""

from __future__ import annotations

from typing import Any

from ai.base import (
    ModelInfo,
    ModelNotLoadedError,
    Predictor,
    ResultKind,
)

__all__ = [
    "AVAILABLE_PREDICTORS",
    "UnavailablePredictor",
    "get_predictor",
    "list_predictors",
]

#: The three problems this project set out to solve. The keys are the stable
#: identifiers used by the API and by `docs/`.
AVAILABLE_PREDICTORS: dict[str, ResultKind] = {
    "fall_detection": "fall_detection",
    "activity_recognition": "activity_recognition",
    "anomaly_detection": "anomaly_detection",
}

#: Which public research dataset each problem will eventually be trained on.
#: Recorded here so the API can state its provenance without reading the
#: dataset documentation at runtime.
PLANNED_DATASETS: dict[str, str] = {
    "fall_detection": "SisFall",
    "activity_recognition": "UCI HAR",
    "anomaly_detection": "CASAS",
}


class UnavailablePredictor:
    """A predictor whose model has not been trained yet.

    Implements the `Predictor` protocol so callers can treat it exactly like a
    real predictor, and always raises `ModelNotLoadedError` from `predict()`.
    It never returns a made-up answer.
    """

    def __init__(self, name: str, kind: ResultKind) -> None:
        self._name = name
        self._kind = kind

    @property
    def info(self) -> ModelInfo:
        """Metadata describing a model that does not exist yet."""
        return ModelInfo(
            name=self._name,
            version="",
            kind=self._kind,
            trained_at=None,
            # Explicitly None: no model means no measured metrics. Putting
            # zeros or placeholders here would fabricate evaluation results.
            metrics=None,
            dataset=PLANNED_DATASETS.get(self._name),
        )

    def is_ready(self) -> bool:
        """Always False: no model file has been produced for this problem."""
        return False

    def predict(self, features: Any) -> Any:
        """Refuse to predict, rather than inventing a result."""
        raise ModelNotLoadedError(
            self._name,
            reason=(
                f"No trained model is available for {self._name!r} yet. "
                f"The planned dataset is {PLANNED_DATASETS.get(self._name, 'not decided')}. "
                "Train the model before calling this predictor."
            ),
        )


def get_predictor(name: str) -> Predictor:
    """Return the predictor registered for `name`.

    Raises `KeyError` for an unknown name, so a typo fails loudly at the call
    site instead of silently returning a placeholder.
    """
    try:
        kind = AVAILABLE_PREDICTORS[name]
    except KeyError:
        raise KeyError(
            f"Unknown predictor {name!r}. Known predictors: "
            f"{sorted(AVAILABLE_PREDICTORS)}"
        ) from None
    return UnavailablePredictor(name, kind)


def list_predictors() -> list[dict[str, Any]]:
    """Describe every predictor and whether it is actually usable.

    This is what the API reports, so an operator can see at a glance that the
    AI features are declared but not yet trained.
    """
    described: list[dict[str, Any]] = []
    for name in AVAILABLE_PREDICTORS:
        predictor = get_predictor(name)
        info = predictor.info
        described.append(
            {
                "name": name,
                "is_ready": predictor.is_ready(),
                "model_version": info.version or None,
                "trained_at": info.trained_at,
                "metrics": info.metrics,
                "dataset": info.dataset,
            }
        )
    return described
