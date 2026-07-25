-- Mining Super-Agent — Initial Schema Migration
-- PostgreSQL 15 + PostGIS + pgvector
-- Run: psql -U mining -d mining -f 001_initial.sql

BEGIN;

-- ── Extensions ──────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS vector;       -- pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- trigram text search
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- UUID generation

-- ── Users ───────────────────────────────────────────────────
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

    -- MFA (TOTP)
    mfa_enabled     BOOLEAN DEFAULT FALSE,
    mfa_secret      VARCHAR(64),
    mfa_backup_codes JSONB,

    -- Session tracking
    max_concurrent_sessions INTEGER DEFAULT 5,
    last_login_at   TIMESTAMPTZ,
    last_login_ip   VARCHAR(45),
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until    TIMESTAMPTZ,

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
CREATE INDEX IF NOT EXISTS idx_users_active ON users (is_active) WHERE is_active = TRUE;

-- ── API Keys (encrypted at rest) ────────────────────────────
CREATE TABLE IF NOT EXISTS api_keys (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    service         VARCHAR(50) NOT NULL,
    encrypted_key   TEXT NOT NULL,
    key_hint        VARCHAR(20),
    is_active       BOOLEAN DEFAULT TRUE,
    last_used_at    TIMESTAMPTZ,
    usage_count     INTEGER DEFAULT 0,
    rate_limit_remaining INTEGER,
    rate_limit_reset_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user_service ON api_keys (user_id, service);
CREATE INDEX IF NOT EXISTS idx_api_keys_service_active ON api_keys (service, is_active) WHERE is_active = TRUE;

-- ── Refresh Tokens ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      VARCHAR(64) NOT NULL UNIQUE,
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked         BOOLEAN DEFAULT FALSE,
    replaced_by     VARCHAR(64),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens (user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens (token_hash);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires ON refresh_tokens (expires_at);

-- ── Geological Units ────────────────────────────────────────
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
CREATE INDEX IF NOT EXISTS idx_geological_units_rock_type ON geological_units (rock_type);
CREATE INDEX IF NOT EXISTS idx_geological_units_name_trgm ON geological_units USING GIN (name gin_trgm_ops);

-- ── Mineral Occurrences ─────────────────────────────────────
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
CREATE INDEX IF NOT EXISTS idx_mineral_occurrences_source ON mineral_occurrences (source);
CREATE INDEX IF NOT EXISTS idx_mineral_occurrences_recorded ON mineral_occurrences (recorded_at);
CREATE INDEX IF NOT EXISTS idx_mineral_occurrences_unit ON mineral_occurrences (geological_unit_id);

-- ── Observations ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS observations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
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
CREATE INDEX IF NOT EXISTS idx_observations_client_id ON observations (client_id) WHERE client_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_observations_observed_at ON observations (observed_at);
CREATE INDEX IF NOT EXISTS idx_observations_mineral ON observations (mineral_occurrence_id);

-- ── Structural Features ─────────────────────────────────────
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
CREATE INDEX IF NOT EXISTS idx_structural_features_type ON structural_features (feature_type);

-- ── Geochemical Samples ─────────────────────────────────────
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
CREATE INDEX IF NOT EXISTS idx_geochemical_samples_id ON geochemical_samples (sample_id);
CREATE INDEX IF NOT EXISTS idx_geochemical_samples_elements ON geochemical_samples USING GIN (elements);

-- ── Mining Sites ────────────────────────────────────────────
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
CREATE INDEX IF NOT EXISTS idx_mining_sites_status ON mining_sites (status);
CREATE INDEX IF NOT EXISTS idx_mining_sites_license ON mining_sites (license_type);

-- ── Embeddings (pgvector) ──────────────────────────────────
-- For RAG pipeline: document chunks with vector embeddings
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
CREATE INDEX IF NOT EXISTS idx_doc_embeddings_source ON document_embeddings (source_table, source_id);

-- ── Rate Limiting (Redis-backed, but table for audit) ──────
CREATE TABLE IF NOT EXISTS rate_limit_log (
    id              BIGSERIAL PRIMARY KEY,
    user_id         INTEGER,
    ip_address      VARCHAR(45),
    endpoint        VARCHAR(255),
    tokens_used     INTEGER,
    blocked         BOOLEAN DEFAULT FALSE,
    recorded_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rate_limit_log_user ON rate_limit_log (user_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_rate_limit_log_ip ON rate_limit_log (ip_address, recorded_at);

-- ── Audit Log ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGSERIAL PRIMARY KEY,
    user_id         INTEGER,
    action          VARCHAR(50) NOT NULL,
    resource_type   VARCHAR(50),
    resource_id     VARCHAR(100),
    details         JSONB,
    ip_address      VARCHAR(45),
    user_agent      TEXT,
    recorded_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log (user_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log (action, recorded_at);

-- ── Updated_at trigger ─────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables with updated_at
DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN
        SELECT unnest(ARRAY[
            'users', 'geological_units', 'observations',
            'mining_sites'
        ])
    LOOP
        EXECUTE format(
            'CREATE TRIGGER update_%s_updated_at '
            'BEFORE UPDATE ON %I '
            'FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()',
            t, t
        );
    END LOOP;
END;
$$;

-- ── Spatial query helper views ──────────────────────────────
-- View: All mineral occurrences within 10km of a point
-- Usage: SELECT * FROM minerals_near_point(-1.0, 34.5, 10000);
CREATE OR REPLACE FUNCTION minerals_near_point(
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    radius_meters DOUBLE PRECISION DEFAULT 10000
)
RETURNS TABLE (
    id INTEGER,
    mineral VARCHAR,
    grade NUMERIC,
    confidence NUMERIC,
    source VARCHAR,
    distance_meters DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        mo.id,
        mo.mineral,
        mo.grade,
        mo.confidence,
        mo.source,
        ST_Distance(
            mo.geom::geography,
            ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography
        ) AS distance_meters
    FROM mineral_occurrences mo
    WHERE ST_DWithin(
        mo.geom::geography,
        ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography,
        radius_meters
    )
    ORDER BY distance_meters;
END;
$$ LANGUAGE plpgsql STABLE;

-- View: Geological unit at a specific point
CREATE OR REPLACE FUNCTION geological_unit_at_point(
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION
)
RETURNS TABLE (
    id INTEGER,
    name VARCHAR,
    age VARCHAR,
    rock_type VARCHAR,
    description TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        gu.id,
        gu.name,
        gu.age,
        gu.rock_type,
        gu.description
    FROM geological_units gu
    WHERE ST_Contains(
        gu.geom,
        ST_SetSRID(ST_MakePoint(lon, lat), 4326)
    );
END;
$$ LANGUAGE plpgsql STABLE;

COMMIT;
