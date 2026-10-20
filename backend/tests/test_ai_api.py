"""Tests for the AI capability endpoints.

These verify the honest behaviour the project promises:

* the API states, in a machine-readable way, that no model is loaded;
* it never returns a fabricated prediction;
* asking a predictor to run returns 503 `MODEL_NOT_LOADED`;
* an unknown predictor name is a 404, not a silent placeholder;
* an unauthenticated caller is rejected like everywhere else.

No dataset, no trained model, and no network access is required.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.identity import User
from backend.tests.conftest import auth_headers, create_user


def _headers(client: TestClient, caregiver_user: User) -> dict[str, str]:
    return auth_headers(client, caregiver_user.email)


# ---------------------------------------------------------------------------
# Listing capabilities
# ---------------------------------------------------------------------------


def test_listing_predictors_admits_nothing_is_ready(
    client: TestClient, caregiver_user: User
) -> None:
    response = client.get("/api/v1/ai/predictors", headers=_headers(client, caregiver_user))

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["any_ready"] is False
    assert len(body["predictors"]) == 3


def test_every_predictor_reports_not_ready_with_no_metrics(
    client: TestClient, caregiver_user: User
) -> None:
    """The API must not present placeholder metrics as real evaluation results."""
    response = client.get("/api/v1/ai/predictors", headers=_headers(client, caregiver_user))
    predictors = response.json()["predictors"]

    for entry in predictors:
        assert entry["is_ready"] is False
        assert entry["metrics"] is None
        assert entry["model_version"] is None
        assert entry["trained_at"] is None


def test_listing_names_the_planned_dataset_for_each_problem(
    client: TestClient, caregiver_user: User
) -> None:
    response = client.get("/api/v1/ai/predictors", headers=_headers(client, caregiver_user))
    by_name = {entry["name"]: entry for entry in response.json()["predictors"]}

    assert by_name["fall_detection"]["dataset"] == "SisFall"
    assert by_name["activity_recognition"]["dataset"] == "UCI HAR"
    assert by_name["anomaly_detection"]["dataset"] == "CASAS"


def test_listing_carries_a_plain_language_note(
    client: TestClient, caregiver_user: User
) -> None:
    """A human reading the response should understand the status immediately."""
    response = client.get("/api/v1/ai/predictors", headers=_headers(client, caregiver_user))
    note = response.json()["note"].lower()

    assert "no ai model" in note
    assert "do not return predictions" in note


def test_listing_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/ai/predictors")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Reading one capability
# ---------------------------------------------------------------------------


def test_reading_one_predictor_reports_not_ready(
    client: TestClient, caregiver_user: User
) -> None:
    response = client.get(
        "/api/v1/ai/predictors/fall_detection", headers=_headers(client, caregiver_user)
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_ready"] is False


def test_unknown_predictor_is_a_404_not_a_placeholder(
    client: TestClient, caregiver_user: User
) -> None:
    response = client.get(
        "/api/v1/ai/predictors/fortune_telling", headers=_headers(client, caregiver_user)
    )

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    # The error should list what *is* available, so the caller can correct itself.
    assert "fall_detection" in body["error"]["details"]["known_predictors"]


# ---------------------------------------------------------------------------
# Asking a predictor to run
# ---------------------------------------------------------------------------


def test_checking_a_predictor_returns_503_model_not_loaded(
    client: TestClient, caregiver_user: User
) -> None:
    """The 'no model' path must be real and verifiable, not just documented."""
    response = client.post(
        "/api/v1/ai/predictors/fall_detection/check",
        headers=_headers(client, caregiver_user),
    )

    assert response.status_code == 503, response.text
    body = response.json()
    assert body["error"]["code"] == "MODEL_NOT_LOADED"
    assert body["error"]["details"]["predictor"] == "fall_detection"
    assert body["error"]["details"]["reason"]


def test_every_predictor_reports_503_rather_than_guessing(
    client: TestClient, caregiver_user: User
) -> None:
    for name in ("fall_detection", "activity_recognition", "anomaly_detection"):
        response = client.post(
            f"/api/v1/ai/predictors/{name}/check",
            headers=_headers(client, caregiver_user),
        )
        assert response.status_code == 503, f"{name} returned {response.status_code}"
        assert response.json()["error"]["code"] == "MODEL_NOT_LOADED"


def test_checking_a_predictor_never_returns_a_predicted_label(
    client: TestClient, caregiver_user: User
) -> None:
    """Guard against a future change that quietly starts returning fake results."""
    response = client.post(
        "/api/v1/ai/predictors/fall_detection/check",
        headers=_headers(client, caregiver_user),
    )
    body = response.json()

    assert response.status_code != 200
    assert "is_fall" not in body
    assert "confidence" not in body


def test_checking_an_unknown_predictor_is_a_404(
    client: TestClient, caregiver_user: User
) -> None:
    response = client.post(
        "/api/v1/ai/predictors/fortune_telling/check",
        headers=_headers(client, caregiver_user),
    )
    assert response.status_code == 404


def test_checking_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/v1/ai/predictors/fall_detection/check")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Any signed-in role may see capabilities (no personal data is involved)
# ---------------------------------------------------------------------------


def test_resident_role_can_see_capabilities(
    client: TestClient, db_session: Session
) -> None:
    """This endpoint exposes no personal data, so it is not role-restricted."""
    from backend.app.models.enums import UserRole

    create_user(db_session, email="resident-ai@example.com", role=UserRole.ELDERLY)
    headers = auth_headers(client, "resident-ai@example.com")

    response = client.get("/api/v1/ai/predictors", headers=headers)

    assert response.status_code == 200, response.text
