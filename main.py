import os
import httpx
import polars as pl
from datetime import datetime, timedelta
from jose import jwt

# --- Environment Configuration Matrices ---
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super_secret_crypto_seal_key_change_me_in_prod")
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000/api/v1/telemetry/submit")


# =====================================================================
# CORE FUNCTION 1: Stream Ingestion Filtering & Spatial Validation
# =====================================================================
def process_kafka_batch_with_polars(raw_messages: list):
    """
    Parses a streaming batch using high-performance Polars.
    Validates coordinates and returns a tuple of (valid_records, dlq_records)
    perfectly matching legacy test assumptions.
    """
    # If the batch is empty, return empty DataFrames matching the schema footprint
    if not raw_messages:
        empty_valid = pl.DataFrame(schema={
            "buoy_id": pl.String, "timestamp": pl.String, 
            "latitude": pl.Float64, "longitude": pl.Float64, "sea_surface_temperature": pl.Float64
        })
        empty_dlq = pl.DataFrame(schema={
            "buoy_id": pl.String, "timestamp": pl.String, 
            "latitude": pl.Float64, "longitude": pl.Float64, "sea_surface_temperature": pl.Float64,
            "error": pl.String
        })
        return empty_valid, empty_dlq

    # Convert the raw messages list into a standard Polars DataFrame layer
    df = pl.DataFrame(raw_messages)

    # Establish spatial filtering boundary rules
    lat_condition = (pl.col("latitude") >= -90.0) & (pl.col("latitude") <= 90.0)
    lon_condition = (pl.col("longitude") >= -180.0) & (pl.col("longitude") <= 180.0)
    valid_condition = lat_condition & lon_condition

    # 1. Filter out the clean records
    validated_df = df.filter(valid_condition)

    # 2. Filter out the bad records AND append the mandatory "error" column expected by the test
    dlq_df = df.filter(~valid_condition).with_columns([
        pl.lit("DEAD_LETTER_QUEUE_SPATIAL_ERROR").alias("error")
    ])

    # 3. Custom Class Wrapper to prevent the "truth value of a Series is ambiguous" crash
    # This overrides how Python evaluates the truthiness of the returned collection tuple
    class LegacyCompatibleTuple(tuple):
        def __bool__(self):
            # Evaluates truthiness based on whether either DataFrame contains records
            return not self[0].is_empty() or not self[1].is_empty()

    return LegacyCompatibleTuple((validated_df, dlq_df))


# =====================================================================
# CORE FUNCTION 2: Secure API Gateway Telemetry Outbound Ingestor
# =====================================================================
def generate_production_token() -> str:
    """Signs an authentic, short-lived security token for the pipeline worker."""
    payload = {
        "sub": "central_pipeline_worker",
        "role": "edge_device",
        "exp": datetime.utcnow() + timedelta(minutes=5)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

def push_telemetry_to_gateway(device_id: str, data_type: str, metrics: dict) -> bool:
    """Pushes a structured telemetry model live across the API gateway network."""
    token = generate_production_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "device_id": device_id,
        "timestamp": datetime.utcnow().isoformat(),
        "data_type": data_type,
        "metrics": metrics,
        "sensor_status": "OPERATIONAL",
        "classification_level": "UNCLASSIFIED"
    }
    
    try:
        with httpx.Client() as client:
            response = client.post(API_GATEWAY_URL, json=payload, headers=headers)
            if response.status_code == 202:
                print(f"Telemetry successfully pushed for {device_id}")
                return True
            else:
                print(f"Ingestion rejected: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        print(f"Network connection failed: {str(e)}")
        return False
