"""AI capability endpoints.

What this router does — and deliberately does not do
----------------------------------------------------
It **reports** which AI capabilities exist and whether each one is usable. It
does **not** fabricate predictions: there is no `/ai/fall-detection/predict`
endpoint that returns a made-up answer, because returning a plausible-looking
fall prediction with no model behind it would be dangerous and dishonest.

When Phase 5 produces real trained models, the prediction endpoints get added
here. They will call `ai.registry.get_predictor(...)`, and a predictor that is
not ready raises `ModelNotLoadedError`, which this module converts into an
honest HTTP 503 (`MODEL_NOT_LOADED`).

Access: any signed-in user may read the capability list. It contains no
personal data — only what the system can and cannot do.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ai.base import ModelNotLoadedError
from ai.registry import AVAILABLE_PREDICTORS, get_predictor, list_predictors
from backend.app.core.deps import get_current_user
from backend.app.core.errors import NotFoundError, ServiceUnavailableError
from backend.app.models.identity import User
from backend.app.schemas.ai import PredictorListResponse, PredictorStatus

router = APIRouter(tags=["AI"])


@router.get(
    "/ai/predictors",
    response_model=PredictorListResponse,
    summary="List the AI capabilities and whether each is usable",
    description=(
        "Reports every AI capability this project declares, together with "
        "whether a trained model is actually loaded for it.\n\n"
        "**Today every entry has `is_ready: false`.** No model has been trained "
        "and no dataset has been downloaded, so this endpoint exists to state "
        "that plainly rather than to serve predictions.\n\n"
        "**Access:** any authenticated user."
    ),
)
def list_ai_predictors(_: User = Depends(get_current_user)) -> PredictorListResponse:
    """Describe each predictor and whether it is genuinely usable."""
    described = list_predictors()
    any_ready = any(entry["is_ready"] for entry in described)

    return PredictorListResponse(
        predictors=[PredictorStatus(**entry) for entry in described],
        any_ready=any_ready,
        note=(
            "No AI model is loaded. These endpoints report capability only; "
            "they do not return predictions."
            if not any_ready
            else "At least one trained model is loaded and usable."
        ),
    )


@router.get(
    "/ai/predictors/{name}",
    response_model=PredictorStatus,
    summary="Describe one AI capability",
    description=(
        "Same information as the list endpoint, for a single predictor.\n\n"
        "Returns **404** for an unknown predictor name, so a typo is reported "
        "rather than silently answered with a placeholder.\n\n"
        "**Access:** any authenticated user."
    ),
)
def get_ai_predictor(
    name: str, _: User = Depends(get_current_user)
) -> PredictorStatus:
    """Describe a single predictor, or 404 when the name is unknown."""
    if name not in AVAILABLE_PREDICTORS:
        raise NotFoundError(
            f"No AI predictor named {name!r} is declared by this API.",
            details={"known_predictors": sorted(AVAILABLE_PREDICTORS)},
        )

    predictor = get_predictor(name)
    info = predictor.info

    return PredictorStatus(
        name=name,
        is_ready=predictor.is_ready(),
        model_version=info.version or None,
        trained_at=info.trained_at,
        metrics=info.metrics,
        dataset=info.dataset,
    )


@router.post(
    "/ai/predictors/{name}/check",
    summary="Confirm whether a predictor can run",
    description=(
        "Asks a predictor to run and reports the outcome.\n\n"
        "This exists so the 'not available yet' behaviour is **verifiable** "
        "rather than merely documented: while no model is trained it always "
        "returns **503** with code `MODEL_NOT_LOADED`.\n\n"
        "It never returns a fabricated prediction. When a real model exists, "
        "this endpoint will return that model's result instead.\n\n"
        "**Access:** any authenticated user."
    ),
    responses={
        503: {
            "description": "No trained model is loaded for this predictor.",
        },
        404: {"description": "Unknown predictor name."},
    },
)
def check_ai_predictor(name: str, _: User = Depends(get_current_user)) -> dict:
    """Attempt inference, reporting honestly when no model is loaded."""
    if name not in AVAILABLE_PREDICTORS:
        raise NotFoundError(
            f"No AI predictor named {name!r} is declared by this API.",
            details={"known_predictors": sorted(AVAILABLE_PREDICTORS)},
        )

    predictor = get_predictor(name)
    try:
        # No features are passed because there is nothing to infer from yet.
        # A real predictor would take a typed feature vector here.
        result = predictor.predict(features=None)
    except ModelNotLoadedError as exc:
        raise ServiceUnavailableError(
            str(exc),
            code="MODEL_NOT_LOADED",
            details={"predictor": name, "reason": exc.reason},
        ) from exc

    # Unreachable while no model exists. Present so the endpoint behaves
    # correctly the moment a real predictor is registered.
    return result.as_dict()  # pragma: no cover
