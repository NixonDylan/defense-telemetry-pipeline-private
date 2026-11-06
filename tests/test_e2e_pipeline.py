import pytest
from fastapi.testclient import TestClient
from main import app  # assuming your FastAPI instance is named 'app' in main.py

client = TestClient(app)

def test_live_end_to_end_pipeline_ingestion():
    """E2E Verification: Pushes data through the FastAPI app and verifies gateway acceptance."""
    test_device = "E2E-CLOUD-BUOY-01"
    mock_payload = {
        "device_id": test_device,
        "data_type": "meteorological",
        "metrics": {"wind_speed_knots": 22.4, "sea_temp_c": 14.8}
    }
    
    # Generate a valid test token or use your auth headers as configured in test_gateway.py
    # Example using direct client post (adjust based on your auth dependency)
    response = client.post(
        "/telemetry/submit", 
        json=mock_payload,
        headers={"Authorization": "Bearer MOCK_VALID_ADMIN_TOKEN"}
    )
    
    assert response.status_code == 200, f"Gateway rejected payload: {response.text}"
    data = response.json()
    assert data.get("status") == "success"
