-- Mining Super-Agent — Initial Schema Migration
-- PostgreSQL 15 + PostGIS + pgvector

BEGIN;

-- Extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) NOT NULL UNIQUE,
    username        VARCHAR(100) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255),
    phone           VARCHAR(30),
    preferred_language VARCHAR(10) DEFAULT 'en',
    is_active       BOOLEAN DEFAULT TRUE,
    is_verified     BOOLEAN DEFAULT FALSE,
    is_admin        BOOLEAN DEFAULT FALSE,
    mfa_enabled     BOOLEAN DEFAULT FALSE,
    mfa_secret      VARCHAR(64),
    mfa_backup_codes JSONB,
    max_concurrent_sessions INTEGER DEFAULT 5,
    last_login_at   TIMESTAMPTZ,
    last_login_ip   VARCHAR(45),
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Rock Types
CREATE TABLE IF NOT EXISTS rock_types (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE,
    classification  VARCHAR(50),
    description     TEXT,
    properties      JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Geological Units
CREATE TABLE IF NOT EXISTS geological_units (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    age             VARCHAR(100),
    rock_type       VARCHAR(100),
    description     TEXT,
    source          VARCHAR(100),
    properties      JSONB,
    geom            GEOMETRY(MultiPolygon, 4326),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_geological_units_geom ON geological_units USING GIST (geom);

-- Mineral Occurrences
CREATE TABLE IF NOT EXISTS mineral_occurrences (
    id              SERIAL PRIMARY KEY,
    mineral         VARCHAR(100) NOT NULL,
    grade           NUMERIC(10, 4),
    grade_unit      VARCHAR(20),
    confidence      NUMERIC(5, 4),
    source          VARCHAR(50) NOT NULL,
    geological_unit_id INTEGER REFERENCES geological_units(id),
    properties      JSONB,
    geom            GEOMETRY(Point, 4326),
    recorded_at     TIMESTAMPTZ DEFAULT NOW(),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mineral_occurrences_geom ON mineral_occurrences USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_mineral_occurrences_mineral ON mineral_occurrences (mineral);

-- Structural Features
CREATE TABLE IF NOT EXISTS structural_features (
    id              SERIAL PRIMARY KEY,
    feature_type    VARCHAR(50) NOT NULL,
    orientation     NUMERIC(8, 3),
    dip             NUMERIC(8, 3),
    dip_direction   NUMERIC(8, 3),
    properties      JSONB,
    geom            GEOMETRY(LineString, 4326),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_structural_features_geom ON structural_features USING GIST (geom);

-- Geochemical Samples
CREATE TABLE IF NOT EXISTS geochemical_samples (
    id              SERIAL PRIMARY KEY,
    sample_id       VARCHAR(50) UNIQUE NOT NULL,
    elements        JSONB NOT NULL,
    sample_type     VARCHAR(50),
    medium          VARCHAR(50),
    properties      JSONB,
    geom            GEOMETRY(Point, 4326),
    collected_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_geochemical_samples_geom ON geochemical_samples USING GIST (geom);

-- Mining Sites
CREATE TABLE IF NOT EXISTS mining_sites (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    status          VARCHAR(50),
    license_type    VARCHAR(50),
    license_number  VARCHAR(100),
    license_expiry  DATE,
    owner_name      VARCHAR(255),
    area_hectares   NUMERIC(10, 3),
    properties      JSONB,
    geom            GEOMETRY(MultiPolygon, 4326),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mining_sites_geom ON mining_sites USING GIST (geom);

-- Observations
CREATE TABLE IF NOT EXISTS observations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER NOT NULL REFERENCES users(id),
    mineral_occurrence_id INTEGER REFERENCES mineral_occurrences(id),
    title           VARCHAR(255),
    description     TEXT,
    photo_urls      JSONB,
    rock_type       VARCHAR(100),
    color           VARCHAR(50),
    luster          VARCHAR(50),
    hardness        NUMERIC(4, 2),
    xrf_data        JSONB,
    ai_analysis     JSONB,
    confidence      NUMERIC(5, 4),
    geom            GEOMETRY(Point, 4326),
    client_id       VARCHAR(36),
    synced          BOOLEAN DEFAULT TRUE,
    observed_at     TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_observations_geom ON observations USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_observations_user ON observations (user_id);

-- Document Embeddings (RAG)
CREATE TABLE IF NOT EXISTS document_embeddings (
    id              BIGSERIAL PRIMARY KEY,
    source_table    VARCHAR(50),
    source_id       INTEGER,
    chunk_text      TEXT NOT NULL,
    chunk_index     INTEGER DEFAULT 0,
    embedding       vector(1024) NOT NULL,
    metadata        JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_doc_embeddings_vector ON document_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Spatial helper: minerals near a point
CREATE OR REPLACE FUNCTION minerals_near_point(
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    radius_meters DOUBLE PRECISION DEFAULT 10000
) RETURNS TABLE (
    id INTEGER, mineral VARCHAR, grade NUMERIC, confidence NUMERIC,
    source VARCHAR, distance_meters DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT mo.id, mo.mineral, mo.grade, mo.confidence, mo.source,
        ST_Distance(mo.geom::geography, ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography) AS distance_meters
    FROM mineral_occurrences mo
    WHERE ST_DWithin(mo.geom::geography, ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography, radius_meters)
    ORDER BY distance_meters;
END;
$$ LANGUAGE plpgsql STABLE;

COMMIT;
