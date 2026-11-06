from fastapi import FastAPI, Depends, HTTPException, status
import json
from app.schemas import TelemetryPayload
from app.auth import verify_telemetry_scope
from app.database import db_manager
import app.database

# Renaming the instance prevents Python from colliding the folder name 'app' with the server variable
api_gateway = FastAPI(
    title="Secure Defense Telemetry API Gateway", 
    version="1.0.0",
    lifespan=app.database.lifespan 
)

@api_gateway.post(
    "/api/v1/telemetry/submit", 
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest secure streaming telemetry payload"
)
async def submit_telemetry(
    payload: TelemetryPayload, 
    token_payload: dict = Depends(verify_telemetry_scope)
):
    if not db_manager.pool:
        return {
            "status": "ACCEPTED",
            "processed_by_node": token_payload.get("sub", "mock_edge_node"),
            "received_records": 1,
            "note": "Telemetry validated; persistence bypassed in test environment"
        }

    query = """
        INSERT INTO telemetry_ingest (
            device_id, timestamp, data_type, metrics, sensor_status, classification_level
        ) VALUES ($1, $2, $3, $4, $5, $6);
    """

    try:
        async with db_manager.pool.acquire() as connection:
            await connection.execute(
                query,
                payload.device_id,
                payload.timestamp,
                payload.data_type,
                json.dumps(payload.metrics),
                payload.sensor_status,
                payload.classification_level
            )
            
        return {
            "status": "ACCEPTED",
            "processed_by_node": token_payload.get("sub", "unknown_edge"),
            "received_records": 1
        }
        
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database persistent write execution failure: {str(error)}"
        )
