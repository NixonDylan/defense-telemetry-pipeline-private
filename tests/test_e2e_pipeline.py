import pytest
from fastapi.testclient import TestClient
from main import api_gateway

client = TestClient(api_gateway)

def test_live_end_to_end_pipeline_ingestion():
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
        headers={"Authorization": "Bearer MOCK_VALID_ADMIN_TOKEN"}
    )
    
    assert response.status_code == 202, f"The API gateway rejected the pipeline telemetry payload: {response.text}"
    data = response.json()
    assert data.get("status") == "ACCEPTED"
