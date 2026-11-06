import os
import httpx
import polars as pl
from datetime import datetime, timedelta
from jose import jwt

# --- 🔐 Environment Configuration Matrices ---
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super_secret_crypto_seal_key_change_me_in_prod")
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000/api/v1/telemetry/submit")

# =====================================================================
# 🚀 CORE FUNCTION 1: Original Polars Pipeline Spatial Processing Logic
# =====================================================================
def process_kafka_batch_with_polars(raw_messages: list) -> pl.DataFrame:
    """
    Parses a streaming batch using high-performance Polars.
    Validates that marine nodes sit inside allowed tracking regions.
    """
    if not raw_messages:
        return pl.DataFrame()

    # Formats raw telemetry rows into an in-memory Polars DataFrame layer
    df = pl.DataFrame(raw_messages)

    # Establish spatial filtering parameters (Example tracking bounding coordinates)
    MIN_LAT, MAX_LAT = -90.0, 90.0
    MIN_LON, MAX_LON = -180.0, 180.0

    # Execute vector filter masks across coordinates
    validated_df = df.filter(
        (pl.col("latitude").is_between(MIN_LAT, MAX_LAT)) &
        (pl.col("longitude").is_between(MIN_LON, MAX_LON))
    )

    return validated_df


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
