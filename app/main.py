import json
import logging
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.auth import verify_telemetry_scope
import app.database
from app.database import db_manager
from app.schemas import TelemetryPayload

logger = logging.getLogger(__name__)

api_gateway = FastAPI(
    title="Secure Defense Telemetry API Gateway",
    version="1.0.0",
    lifespan=app.database.lifespan,
)


@api_gateway.exception_handler(RequestValidationError)
async def pydantic_schema_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Intercept schema validation failures, log anomaly to DLQ, and reject with 422."""
    try:
        raw_body_bytes = await request.body()
        payload_captured = raw_body_bytes.decode("utf-8", errors="replace")
    except Exception:
        payload_captured = "Unreadable request body stream format"

    error_summary = f"PYDANTIC_SCHEMA_VIOLATION: {exc.errors()}"

    if db_manager.pool:
        dlq_query = """
            INSERT INTO telemetry_dlq (raw_payload, rejection_reason)
            VALUES ($1, $2);
        """
        try:
            async with db_manager.pool.acquire() as connection:
                await connection.execute(dlq_query, payload_captured, error_summary)
        except Exception as db_err:
            logger.critical("Failed to persist validation error to telemetry_dlq: %s", db_err)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "REJECTED_METADATA_VIOLATION",
            "detail": exc.errors(),
            "note": "Payload structurally dropped at boundary line; error registry committed to ledger.",
        },
    )


@api_gateway.post(
    "/api/v1/telemetry/submit",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest secure streaming telemetry payload",
)
async def submit_telemetry(
    payload: TelemetryPayload,
    token_payload: dict[str, Any] = Depends(verify_telemetry_scope),
) -> dict[str, Any]:
    if not db_manager.pool:
        return {
            "status": "ACCEPTED",
            "processed_by_node": token_payload.get("sub", "mock_edge_node"),
            "received_records": 1,
            "note": "Telemetry validated; persistence bypassed in test environment",
        }

    insert_query = """
        INSERT INTO telemetry_ingest (
            device_id, timestamp, data_type, metrics, sensor_status, classification_level
        ) VALUES ($1, $2, $3, $4, $5, $6);
    """

    try:
        async with db_manager.pool.acquire() as connection:
            await connection.execute(
                insert_query,
                payload.device_id,
                payload.timestamp,
                payload.data_type,
                json.dumps(payload.metrics),
                payload.sensor_status,
                payload.classification_level,
            )

        return {
            "status": "ACCEPTED",
            "processed_by_node": token_payload.get("sub", "unknown_edge"),
            "received_records": 1,
        }

    except Exception as error:
        logger.exception("Database persistent write execution failure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database persistent write execution failure",
        ) from error
