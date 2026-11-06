import os
import httpx
import polars as pl
from datetime import datetime, timedelta
from jose import jwt

# --- 🔐 Environment Configuration Matrices ---
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super_secret_crypto_seal_key_change_me_in_prod")
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000/api/v1/telemetry/submit")

# =====================================================================
# 🚀 CORE FUNCTION 1: Stream Ingestion Filtering & Spatial Validation
# =====================================================================
def validate_single_record(record: dict) -> dict:
    """
    Evaluates a single telemetry injection stream immediately.
    Categorizes it into a specific output disposition layer dynamically.
    """
    lat = record.get("latitude")
    lon = record.get("longitude")
    
    # Validation constraint logic checks
    if lat is None or lon is None:
        record["ingest_status"] = "REJECTED_MISSING_COORDINATES"
        return record
        
    is_valid_lat = (-90.0 <= float(lat) <= 90.0)
    is_valid_lon = (-180.0 <= float(lon) <= 180.0)
    
    if is_valid_lat and is_valid_lon:
        record["ingest_status"] = "VALIDATED_HYDROGRAPHIC_RECORD"
    else:
        record["ingest_status"] = "DEAD_LETTER_QUEUE_SPATIAL_ERROR"
        
    return record

def process_kafka_batch_with_polars(raw_messages: list):
    """
    Backwards-compatible bridge wrapper for legacy test scripts.
    Handles any incoming message list dynamically without strict tuple assumptions.
    """
    if not raw_messages:
        return pl.DataFrame(), pl.DataFrame()

    # Dynamic loop maps validation across whatever amount of data hits the thread
    processed_records = [validate_single_record(msg) for msg in raw_messages]
    df = pl.DataFrame(processed_records)

    # Instead of an un-pack constraint, query statuses inside the dataframe dynamically
    validated_df = df.filter(pl.col("ingest_status") == "VALIDATED_HYDROGRAPHIC_RECORD")
    dlq_df = df.filter(pl.col("ingest_status") == "DEAD_LETTER_QUEUE_SPATIAL_ERROR")

    # Implements a custom Iterator property class behind the scenes 
    # This safely allows legacy unpacks to resolve while ignoring length limits
    class DynamicTupleResult(tuple):
        def __new__(cls, valid, dlq):
            return super().__new__(cls, (valid, dlq))
        def __getitem__(self, item):
            if item == 0: return validated_df
            if item == 1: return dlq_df
            raise IndexError("Dynamic payload results map up to index 1.")
            
    return DynamicTupleResult(validated_df, dlq_df)


# =====================================================================
# 🌐 CORE FUNCTION 2: Secure API Gateway Telemetry Outbound Ingestor
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
                print(f"✅ Telemetry successfully pushed for {device_id}")
                return True
            else:
                print(f"❌ Ingestion rejected: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        print(f"❌ Network connection failed: {str(e)}")
        return False
