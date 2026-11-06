-- Enable the PostGIS spatial extension inside the telemetry database
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create the primary ingestion destination table
CREATE TABLE IF NOT EXISTS telemetry_table (
    id BIGSERIAL,
    buoy_id VARCHAR(50) NOT NULL,
    time TIMESTAMPTZ NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    sea_surface_temperature DOUBLE PRECISION,

    
    -- SENIOR PATTERN: PostGIS automatically calculates the geometry point directly 
    -- from latitude and longitude variables on write, entirely bypassing post-ingestion table scans.
    geom geometry(Point, 4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)) STORED,
    
    PRIMARY KEY (id, time)
);

-- Index the geometry column for ultra-fast spatial and geographical API queries
CREATE INDEX IF NOT EXISTS telemetry_spatial_idx ON telemetry_table USING GIST (geom);
-- Index time series for rapid ERDDAP rendering sequential lookups
CREATE INDEX IF NOT EXISTS telemetry_time_idx ON telemetry_table (time DESC);

-- Create your Dead Letter Queue table to catch Pydantic validation failures
CREATE TABLE IF NOT EXISTS telemetry_dlq (
    source_topic    TEXT NOT NULL DEFAULT 'buoy_telemetry_stream',
    payload_raw     JSONB NOT NULL,
    errors          JSONB NOT NULL,
    received_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status          TEXT NOT NULL DEFAULT 'pending'
);
