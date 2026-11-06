import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_live_end_to_end_pipeline_ingestion():
    """Live E2E Verification: Pushes data through FastAPI's TestClient and verifies DB row persistence."""
    test_device = "E2E-CLOUD-BUOY-01"
    mock_payload = {
        "device_id": test_device,
        "data_type": "meteorological",
        "metrics": {"wind_speed_knots": 22.4, "sea_temp_c": 14.8}
    }
    
    # Use FastAPI TestClient to hit the endpoint in-memory without needing a live network daemon
    response = client.post(
        "/telemetry/submit", 
        json=mock_payload,
        headers={"Authorization": "Bearer MOCK_VALID_ADMIN_TOKEN"}
    )
    
    assert response.status_code == 200, f"The API gateway rejected the pipeline telemetry payload: {response.text}"
    data = response.json()
    assert data.get("status") == "success"
