import os
import time
import pytest
import psycopg
from app.config import settings

# Construct the live connection string targeting the database container port mapping
DB_URL = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@localhost:5432/{settings.POSTGRES_DB}"

def test_live_end_to_end_pipeline_ingestion():
    """Live E2E Verification: Pushes data through main.py and verifies DB row persistence."""
    
    # 1. Import your updated live payload pusher from the main module layout
    from main import push_telemetry_to_gateway
    
    # 2. Fire an authentic telemetry payload across the local Codespace container network bridge
    test_device = "E2E-CLOUD-BUOY-01"
    mock_metrics = {"wind_speed_knots": 22.4, "sea_temp_c": 14.8}
    
    success = push_telemetry_to_gateway(
        device_id=test_device,
        data_type="meteorological",
        metrics=mock_metrics
    )
    
    assert success is True, "The API gateway rejected the pipeline telemetry payload!"
    
    # 3. Pause briefly to allow the FastAPI background asyncpg queue pool to commit to disk
    time.sleep(0.5)
    
    # 4. Query the live PostgreSQL service directly to prove data persistence holds true
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT device_id, data_type FROM telemetry_ingest WHERE device_id = %s;",
                (test_device,)
            )
            record = cursor.fetchone()
            
            # --- THE ULTIMATE PROOF ---
            assert record is not None, "E2E Failure: Telemetry record was never written to the PostgreSQL database!"
            assert record[0] == test_device, "Data corruption detected in stored device ID field."
            assert record[1] == "meteorological", "Data corruption detected in data type mapping."
