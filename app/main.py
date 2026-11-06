from fastapi import FastAPI, Depends, HTTPException, status
import json
from app.schemas import TelemetryPayload
from app.auth import verify_telemetry_scope
from app.database import db_manager, lifespan

app = FastAPI(
    title="Secure Defense Telemetry API Gateway", 
    version="1.0.0",
    lifespan=lifespan # Binds the async database pool lifecycle
)

@app.post(
    "/api/v1/telemetry/submit", 
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest secure streaming telemetry payload"
)
async def submit_telemetry(
    payload: TelemetryPayload, 
    token_payload: dict = Depends(verify_telemetry_scope)
):
    # Ensure the database pool is running and responsive
    if not db_manager.pool:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection pool is uninitialized"
        )

    # Construct the SQL execution layout
    # (Matches standard table column structures defined in your repository initialization layouts)
    query = """
        INSERT INTO telemetry_ingest (
            device_id, timestamp, data_type, metrics, sensor_status, classification_level
        ) VALUES ($1, $2, $3, $4, $5, $6);
    """

    try:
        # Acquire an active, non-blocking connection channel from the warm pool
        async with db_manager.pool.acquire() as connection:
            await connection.execute(
                query,
                payload.device_id,
                payload.timestamp,
                payload.data_type,
                json.dumps(payload.metrics), # Cast Python dictionary to JSON string string for native PG JSONB storage
                payload.sensor_status,
                payload.classification_level
            )
            
        return {
            "status": "ACCEPTED",
            "processed_by_node": token_payload.get("sub", "unknown_edge"),
            "received_records": 1
        }
        
    except Exception as error:
        # Fallback to catch structural errors or unique database constraint drops under load
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database persistent write execution failure: {str(error)}"
        )
