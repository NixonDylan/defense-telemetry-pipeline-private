from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi.testclient import TestClient
from jose import jwt

from app.config import settings
from app.main import api_gateway


def generate_test_token(payload: dict[str, Any]) -> str:
    to_encode = payload.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(minutes=15)
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def test_telemetry_ingestion_endpoint_accepts_valid_payload() -> None:
    """Verify /api/v1/telemetry/submit accepts a valid JWT and telemetry payload."""
    token = generate_test_token(
        {"sub": "edge_node_alpha", "role": "admin", "scopes": ["telemetry:submit"]}
    )

    mock_payload: dict[str, Any] = {
        "device_id": "E2E-CLOUD-BUOY-01",
        "timestamp": "2026-11-06T16:00:00Z",
        "data_type": "meteorological",
        "metrics": {
            "latitude": 29.5,
            "longitude": -89.2,
            "wind_speed_knots": 22.4,
            "sea_temp_c": 14.8,
        },
        "sensor_status": "nominal",
        "classification_level": "UNCLASSIFIED",
    }

    with TestClient(api_gateway) as client:
        response = client.post(
            "/api/v1/telemetry/submit",
            json=mock_payload,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 202, (
        f"The API gateway rejected the pipeline telemetry payload: {response.text}"
    )
    data = response.json()
    assert data.get("status") == "ACCEPTED"
    assert data.get("received_records") == 1
