import pytest
from fastapi.testclient import TestClient
from main import api_gateway
from tests.test_gateway import create_access_token

client = TestClient(api_gateway)

def test_live_end_to_end_pipeline_ingestion():
    """Live E2E Verification: Pushes data through FastAPI's TestClient with a valid signed token."""
    token = create_access_token(data={"sub": "edge_node_alpha", "role": "admin", "scopes": ["telemetry:submit"]})
    
    mock_payload = {
        "device_id": "E2E-CLOUD-BUOY-01",
        "timestamp": "2026-11-06T16:00:00Z",
        "data_type": "meteorological",
        "metrics": {"wind_speed_knots": 22.4, "sea_temp_c": 14.8},
        "sensor_status": "nominal",
        "classification_level": "UNCLASSIFIED"
    }
    
    response = client.post(
        "/api/v1/telemetry/submit", 
        json=mock_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 202, f"The API gateway rejected the pipeline telemetry payload: {response.text}"
    data = response.json()
    assert data.get("status") == "ACCEPTED"
