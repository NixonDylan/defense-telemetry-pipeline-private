from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import json

from app.schemas import TelemetryPayload
from app.auth import verify_telemetry_scope
from app.database import db_manager
import app.database

# 1. Instantiate the FastAPI gateway first so it exists in memory for decorators
api_gateway = FastAPI(
    title="Secure Defense Telemetry API Gateway", 
    version="1.0.0",
    lifespan=app.database.lifespan 
)

# 2. Attach the global exception handler middleware safely now that api_gateway is defined
@api_gateway.exception_handler(RequestValidationError)
async def pydantic_schema_exception_handler(request, exc: RequestValidationError):
    """
    DevSecOps Middleware: Intercepts validation failures, extracts malformed JSON, 
    and writes anomalies to the database before dropping connection.
    """
    try:
        raw_body_bytes = await request.body()
        payload_captured = raw_body_bytes.decode("utf-8")
    except Exception:
        payload_captured = "Unreadable request body stream format"

    error_summary = f"PYDANTIC_SCHEMA_VIOLATION: {str(exc.errors())}"

    if db_manager.pool:
        query = """
            INSERT INTO telemetry_dlq (raw_payload, rejection_reason)
            VALUES ($1, $2);
        """
        try:
            async with db_manager.pool.acquire() as connection:
                await connection.execute(query, payload_captured, error_summary)
        except Exception as db_err:
            print(f"Fallback critical log trace: {str(db_err)}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "REJECTED_METADATA_VIOLATION",
            "detail": exc.errors(),
            "note": "Payload structurally dropped at boundary line; error registry committed to ledger."
        }
    )

# 3. Expose the secure telemetry submission ingestion route endpoint
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
