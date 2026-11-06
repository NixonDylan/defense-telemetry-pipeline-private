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
    
    assert response.status_code == 202, (
        f"Gateway rejected payload. Status: {response.status_code}, Body: {response.text}"
    )
    data = response.json()
    assert data.get("status") == "ACCEPTED"
