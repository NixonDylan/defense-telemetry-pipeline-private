import os
import pytest
from main import process_kafka_batch_with_polars

def test_polars_spatial_validation_valid():
    """Test that valid spatial coordinates pass through Polars validation correctly."""
    batch = [
        {"buoy_id": "TEST-BUOY", "timestamp": "2026-11-05T08:00:00Z", "latitude": 30.2, "longitude": -89.7, "sea_surface_temperature": 21.4}
    ]
    valid_records, dlq_records = process_kafka_batch_with_polars(batch)
    
    assert len(valid_records) == 1
    assert len(dlq_records) == 0
    assert valid_records[0]["buoy_id"] == "TEST-BUOY"

def test_polars_spatial_validation_invalid():
    """Test that out-of-bounds coordinates get caught and sent to the DLQ batch."""
    batch = [
        {"buoy_id": "BAD-BUOY", "timestamp": "2026-11-05T08:00:00Z", "latitude": 150.0, "longitude": -89.7, "sea_surface_temperature": 0.0}
    ]
    valid_records, dlq_records = process_kafka_batch_with_polars(batch)
    
    assert len(valid_records) == 0
    assert len(dlq_records) == 1
    assert "Out of bounds spatial coordinates" in dlq_records[0]["error"]
