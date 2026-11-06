import pytest
from datetime import datetime, timedelta
from fastapi import status
from fastapi.testclient import TestClient
from jose import jwt
from unittest.mock import MagicMock

from app.main import app
from app.config import settings
import app.main

def generate_mock_jwt(subject: str, role: str, expires_delta: int = 15) -> str:
    """Helper utility to sign valid mock tokens for specific security scopes"""
    payload = {
        "sub": subject,
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=expires_delta)
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def test_client():
    """Provides an isolated TestClient instance utilizing a clean with-context block"""
    app.main.db_manager.pool = MagicMock()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def valid_telemetry_payload():
    return {
        "device_id": "EDGE-TEST-NODE-99",
        "timestamp": datetime.utcnow().isoformat(),
        "data_type": "meteorological",
        "metrics": {"wind_speed_knots": 18.4, "sea_temp_c": 12.1},
        "sensor_status": "OPERATIONAL",
        "classification_level": "UNCLASSIFIED"
    }


def test_submit_telemetry_without_auth(test_client, valid_telemetry_payload):
    """Ensure anonymous API execution is completely blocked"""
    response = test_client.post("/api/v1/telemetry/submit", json=valid_telemetry_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_submit_telemetry_with_invalid_role(test_client, valid_telemetry_payload):
    """Ensure authorized accounts lacking RBAC clearing scopes are rejected"""
    token = generate_mock_jwt(subject="untrusted_client", role="guest")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = test_client.post("/api/v1/telemetry/submit", json=valid_telemetry_payload, headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Insufficient permissions for telemetry ingestion"


def test_submit_telemetry_success(test_client, valid_telemetry_payload):
    """Validate E2E happy path: correct schema, authentic crypto token, approved role"""
    token = generate_mock_jwt(subject="buoy_station_alpha", role="edge_device")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = test_client.post("/api/v1/telemetry/submit", json=valid_telemetry_payload, headers=headers)
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["status"] == "ACCEPTED"
    assert response.json()["processed_by_node"] == "buoy_station_alpha"


def test_submit_telemetry_invalid_schema(test_client):
    """Ensure Pydantic v2 boundary guard filters out corrupted metadata structures"""
    token = generate_mock_jwt(subject="buoy_station_alpha", role="edge_device")
    headers = {"Authorization": f"Bearer {token}"}
    
    corrupted_payload = {
        "device_id": "EDGE-TEST-NODE-99",
        "sensor_status": "FAULTY"
    }
    
    response = test_client.post("/api/v1/telemetry/submit", json=corrupted_payload, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
