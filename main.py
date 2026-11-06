import os
import httpx
from datetime import datetime, timedelta
from jose import jwt

# Dynamically fall back to local dev container network routing if variables aren't set
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super_secret_crypto_seal_key_change_me_in_prod")
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000/api/v1/telemetry/submit")

def generate_production_token() -> str:
    """Signs an authentic, short-lived security token for the pipeline worker."""
    payload = {
        "sub": "central_pipeline_worker",
        "role": "edge_device",
        "exp": datetime.utcnow() + timedelta(minutes=5)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

def push_telemetry_to_gateway(device_id: str, data_type: str, metrics: dict):
    """Pushes a structured telemetry model live across the API gateway."""
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
    
    with httpx.Client() as client:
        response = client.post(API_GATEWAY_URL, json=payload, headers=headers)
        if response.status_code == 202:
            print(f"✅ Telemetry successfully pushed for {device_id}")
            return True
        else:
            print(f"❌ Ingestion rejected: {response.status_code} - {response.text}")
            return False
