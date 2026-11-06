import os
import json
import polars as pl
import psycopg
from psycopg_pool import ConnectionPool
from datetime import datetime
from io import BytesIO
import logging
import time
from celery import Celery

# -------------------------------------------------------------------------
# CONFIGURATION, BROKER & POOL INITIALIZATION
# -------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://redis_broker:6379/0")
DB_CONN_STRING = os.getenv("DATABASE_URL", "postgresql://admin:secure_password123@localhost:5432/telemetry")

# Initialize Celery App instance
celery_app = Celery("telemetry_pipeline", broker=REDIS_URL, backend=REDIS_URL)

# Thread-safe connection pool shared across tasks
db_pool = ConnectionPool(conninfo=DB_CONN_STRING, min_size=2, max_size=10, open=True)

# -------------------------------------------------------------------------
# PHASE 2: VECTORIZED VALIDATION LAYER (REPLACES PYDANTIC LOOP)
# -------------------------------------------------------------------------
def process_kafka_batch_with_polars(raw_json_messages: list) -> tuple[list, list]:
    """
    Validates streaming payloads using multi-threaded Polars expressions.
    Returns clean, primitive Python dictionaries split into valid and invalid sets.
    """
    if not raw_json_messages:
        return [], []

    # 1. Load batch directly into a Polars DataFrame
    df = pl.DataFrame(raw_json_messages)

    # Ensure timestamp column is cast properly to datetime types
    if df["timestamp"].dtype == pl.String:
        df = df.with_columns(pl.col("timestamp").str.to_datetime(format="%Y-%m-%dT%H:%M:%SZ"))

    # 2. Vectorized checking using Rust-native execution speeds
    spatial_mask = (pl.col("latitude").is_between(-90, 90)) & (pl.col("longitude").is_between(-180, 180))
    
    valid_df = df.filter(spatial_mask)
    invalid_df = df.filter(~spatial_mask)

    # 3. Format valid items for Redis serialization
    valid_records = []
    if len(valid_df) > 0:
        # Convert datetimes to ISO strings dynamically
        valid_df = valid_df.with_columns(pl.col("timestamp").dt.to_string("%Y-%m-%dT%H:%M:%SZ"))
        valid_records = valid_df.to_dicts()

    # 4. Format invalid items into Dead-Letter format
    dlq_records = []
    for row in invalid_df.to_dicts():
        dlq_records.append({
            "payload": row,
            "error": "Out of bounds spatial coordinates detected via Polars filter."
        })

    return valid_records, dlq_records

# -------------------------------------------------------------------------
# PHASE 3: DECOUPLED BULK STORAGE INGESTION (CONSUMER/WORKER SIDE)
# -------------------------------------------------------------------------
@celery_app.task(name="main.async_bulk_insert_to_postgis")
def async_bulk_insert_to_postgis(valid_records: list):
    """
    Asynchronous Celery task pulling data off Redis and copying it to PostGIS.
    """
    if not valid_records:
        return "Empty batch skipped."

    logging.info(f"Worker processing bulk batch of {len(valid_records)} records...")
    
    # Instantiate DataFrame and rename timestamp to match database column layout
    df = pl.DataFrame(valid_records).rename({"timestamp": "time"})

    buffer = BytesIO()
    df.write_csv(buffer, include_header=False)
    buffer.seek(0) 
    
    try:
        with db_pool.connection() as conn:
            with conn.cursor() as cur:
                with cur.copy(
                    "COPY telemetry_table (buoy_id, time, latitude, longitude, sea_surface_temperature) FROM STDIN WITH (FORMAT CSV)"
                ) as copy:
                    copy.write(buffer.read())
            conn.commit()
        logging.info(f"Successfully executed native COPY operation for {len(df)} records into PostGIS.")
        return f"Ingested {len(df)} records successfully."
    except Exception as e:
        logging.critical(f"Database bulk ingestion failed on worker tier: {str(e)}")
        raise e

# -------------------------------------------------------------------------
# INGESTION ENTRYPOINT LOOP (PRODUCER EXECUTION)
# -------------------------------------------------------------------------
if __name__ == "__main__":
    logging.info("Starting primary Ingestion Boundary service loop...")
    
    mock_stream_source = [
        {"buoy_id": "BUOY-001", "timestamp": "2026-11-05T08:00:00Z", "latitude": 30.2, "longitude": -89.7, "sea_surface_temperature": 21.4},
        {"buoy_id": "BUOY-002", "timestamp": "2026-11-05T08:01:00Z", "latitude": 31.5, "longitude": -88.9, "sea_surface_temperature": 22.1},
        {"buoy_id": "BAD-DATA", "timestamp": "2026-11-05T08:02:00Z", "latitude": 105.0, "longitude": -88.9, "sea_surface_temperature": 0.0}
    ]

    while True:
        logging.info("Polling stream for new batch data...")
        
        # 1. Ingest & Validate via Vectorized Polars Engine
        valid_batch, dlq_batch = process_kafka_batch_with_polars(mock_stream_source)
        
        # 2. Sink failures to telemetry_dlq table instantly using the connection pool
        if dlq_batch:
            logging.warning(f"Sinking {len(dlq_batch)} corrupted items to the telemetry_dlq table.")
            try:
                with db_pool.connection() as conn:
                    with conn.cursor() as cur:
                        for item in dlq_batch:
                            cur.execute(
                                """
                                INSERT INTO telemetry_dlq (payload_raw, errors)
                                VALUES (%s, %s)
                                """,
                                (json.dumps(item["payload"]), json.dumps({"reason": item["error"]}))
                            )
                    conn.commit()
            except Exception as database_error:
                logging.error(f"Failed to record failures to telemetry_dlq database: {database_error}")

        # 3. Offload clean batches to background tier via Celery
        if valid_batch:
            logging.info(f"Dispatching task to Redis queue for asynchronous processing.")
            async_bulk_insert_to_postgis.delay(valid_batch)
            
        time.sleep(10)
