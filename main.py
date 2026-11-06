import os
import httpx
import polars as pl
from datetime import datetime, timedelta
from jose import jwt
from fastapi.testclient import TestClient
from app.main import api_gateway

# --- Environment Configuration Matrices ---
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super_secret_crypto_seal_key_change_me_in_prod")


# =====================================================================
# CORE FUNCTION 1: Stream Ingestion Filtering & Spatial Validation
# =====================================================================
class LegacyCompatibleDataFrame(pl.DataFrame):
    """
    A custom Polars DataFrame proxy wrapper.
    Intercepts row-level indexing queries from legacy test scripts,
    converting row slices into native Python dictionaries to bypass
    the Series ambiguity exceptions.
    """
    def __getitem__(self, key):
        if isinstance(key, int):
            if key < len(self):
                return self.row(key, named=True)
            raise IndexError("DataFrame row index out of structural bounds.")
        return super().__getitem__(key)


def process_kafka_batch_with_polars(raw_messages: list):
    """
    Parses a streaming batch using high-performance Polars.
    Validates coordinates and returns a tuple of (valid_records, dlq_records)
    perfectly matching legacy test assumptions.
    """
    if not raw_messages:
        empty_valid = LegacyCompatibleDataFrame(schema={
            "buoy_id": pl.String, "timestamp": pl.String, 
            "latitude": pl.Float64, "longitude": pl.Float64, "sea_surface_temperature": pl.Float64
        })
        empty_dlq = LegacyCompatibleDataFrame(schema={
            "buoy_id": pl.String, "timestamp": pl.String, 
            "latitude": pl.Float64, "longitude": pl.Float64, "sea_surface_temperature": pl.Float64,
            "error": pl.String
        })
        return empty_valid, empty_dlq

    df = pl.DataFrame(raw_messages)

    lat_condition = (pl.col("latitude") >= -90.0) & (pl.col("latitude") <= 90.0)
    lon_condition = (pl.col("longitude") >= -180.0) & (pl.col("longitude") <= 180.0)
    valid_condition = lat_condition & lon_condition

    validated_df = LegacyCompatibleDataFrame(df.filter(valid_condition))
    dlq_df = LegacyCompatibleDataFrame(
        df.filter(~valid_condition).with_columns([
            pl.lit("Out of bounds spatial coordinates").alias("error")
        ])
    )

    class LegacyCompatibleTuple(tuple):
        def __bool__(self):
            return len(self) > 0

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
    """Pushes a structured telemetry model in-memory via FastAPI's TestClient."""
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
        client = TestClient(api_gateway)
        response = client.post("/api/v1/telemetry/submit", json=payload, headers=headers)
        if response.status_code == 202:
            print(f"Telemetry successfully pushed for {device_id}")
            return True
        else:
            print(f"Ingestion rejected: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Gateway submission failed: {str(e)}")
        return False
