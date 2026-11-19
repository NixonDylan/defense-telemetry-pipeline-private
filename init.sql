-- Enable the PostGIS spatial extension inside the telemetry database
CREATE EXTENSION IF NOT EXISTS postgis;

-- Drop legacy schema tables if re-initializing
DROP TABLE IF EXISTS telemetry_table CASCADE;
DROP TABLE IF EXISTS telemetry_ingest CASCADE;
DROP TABLE IF EXISTS telemetry_dlq CASCADE;

-- Create the primary ingestion destination table matching app/main.py
CREATE TABLE telemetry_ingest (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    data_type VARCHAR(50) NOT NULL,
    metrics JSONB NOT NULL,
    sensor_status VARCHAR(50) NOT NULL,
    classification_level VARCHAR(50) NOT NULL DEFAULT 'UNCLASSIFIED',
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index device_id and timestamp for rapid time-series queries
CREATE INDEX telemetry_ingest_device_idx ON telemetry_ingest (device_id);
CREATE INDEX telemetry_ingest_time_idx ON telemetry_ingest (timestamp DESC);

-- Create the Dead Letter Queue (DLQ) table matching app/main.py global exception middleware
CREATE TABLE telemetry_dlq (
    id BIGSERIAL PRIMARY KEY,
    raw_payload TEXT NOT NULL,
    rejection_reason TEXT NOT NULL,
    rejected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
