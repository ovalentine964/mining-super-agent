"""Initial schema — all core tables with PostGIS + pgvector.

Revision ID: 001_initial
Revises: None
Create Date: 2026-07-25 16:18:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from geoalchemy2 import Geometry
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Extensions ──────────────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis_topology')
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ── users ───────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("preferred_language", sa.String(10), server_default="en"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("is_verified", sa.Boolean(), server_default="false"),
        sa.Column("is_admin", sa.Boolean(), server_default="false"),
        sa.Column("mfa_enabled", sa.Boolean(), server_default="false"),
        sa.Column("mfa_secret", sa.String(512), nullable=True),
        sa.Column("mfa_backup_codes", JSONB, nullable=True),
        sa.Column("max_concurrent_sessions", sa.Integer(), server_default="5"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_ip", sa.String(45), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # ── rock_types ──────────────────────────────────────────────────────
    op.create_table(
        "rock_types",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("classification", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("properties", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # ── geological_units ────────────────────────────────────────────────
    op.create_table(
        "geological_units",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("age", sa.String(100), nullable=True),
        sa.Column("rock_type", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("properties", JSONB, nullable=True),
        sa.Column("geom", Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_geological_units_name", "geological_units", ["name"])
    op.create_index("ix_geological_units_rock_type", "geological_units", ["rock_type"])
    op.execute("CREATE INDEX IF NOT EXISTS idx_geological_units_geom ON geological_units USING GIST (geom)")

    # ── mineral_occurrences ─────────────────────────────────────────────
    op.create_table(
        "mineral_occurrences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("mineral", sa.String(100), nullable=False),
        sa.Column("grade", sa.Numeric(10, 4), nullable=True),
        sa.Column("grade_unit", sa.String(20), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("geological_unit_id", sa.Integer(), sa.ForeignKey("geological_units.id"), nullable=True),
        sa.Column("properties", JSONB, nullable=True),
        sa.Column("geom", Geometry(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mineral_occurrences_mineral", "mineral_occurrences", ["mineral"])
    op.create_index("ix_mineral_occurrences_source", "mineral_occurrences", ["source"])
    op.execute("CREATE INDEX IF NOT EXISTS idx_mineral_occurrences_geom ON mineral_occurrences USING GIST (geom)")

    # ── structural_features ─────────────────────────────────────────────
    op.create_table(
        "structural_features",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("feature_type", sa.String(50), nullable=False),
        sa.Column("orientation", sa.Numeric(8, 3), nullable=True),
        sa.Column("dip", sa.Numeric(8, 3), nullable=True),
        sa.Column("dip_direction", sa.Numeric(8, 3), nullable=True),
        sa.Column("properties", JSONB, nullable=True),
        sa.Column("geom", Geometry(geometry_type="LINESTRING", srid=4326), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_structural_features_geom ON structural_features USING GIST (geom)")

    # ── geochemical_samples ─────────────────────────────────────────────
    op.create_table(
        "geochemical_samples",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sample_id", sa.String(50), nullable=False),
        sa.Column("elements", JSONB, nullable=False),
        sa.Column("sample_type", sa.String(50), nullable=True),
        sa.Column("medium", sa.String(50), nullable=True),
        sa.Column("properties", JSONB, nullable=True),
        sa.Column("geom", Geometry(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sample_id"),
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_geochemical_samples_geom ON geochemical_samples USING GIST (geom)")

    # ── mining_sites ────────────────────────────────────────────────────
    op.create_table(
        "mining_sites",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("license_type", sa.String(50), nullable=True),
        sa.Column("license_number", sa.String(100), nullable=True),
        sa.Column("license_expiry", sa.Date(), nullable=True),
        sa.Column("owner_name", sa.String(255), nullable=True),
        sa.Column("area_hectares", sa.Numeric(10, 3), nullable=True),
        sa.Column("properties", JSONB, nullable=True),
        sa.Column("geom", Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_mining_sites_geom ON mining_sites USING GIST (geom)")

    # ── observations ────────────────────────────────────────────────────
    op.create_table(
        "observations",
        sa.Column("id", UUID(as_uuid=True), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("mineral_occurrence_id", sa.Integer(), sa.ForeignKey("mineral_occurrences.id"), nullable=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("photo_urls", JSONB, nullable=True),
        sa.Column("rock_type", sa.String(100), nullable=True),
        sa.Column("color", sa.String(50), nullable=True),
        sa.Column("luster", sa.String(50), nullable=True),
        sa.Column("hardness", sa.Numeric(4, 2), nullable=True),
        sa.Column("xrf_data", JSONB, nullable=True),
        sa.Column("ai_analysis", JSONB, nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("geom", Geometry(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("client_id", sa.String(36), nullable=True),
        sa.Column("synced", sa.Boolean(), server_default="true"),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_observations_user_id", "observations", ["user_id"])
    op.execute("CREATE INDEX IF NOT EXISTS idx_observations_geom ON observations USING GIST (geom)")

    # ── document_embeddings (pgvector RAG) ──────────────────────────────
    op.create_table(
        "document_embeddings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source_table", sa.String(50), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), server_default="0"),
        sa.Column("embedding", sa.Text(), nullable=False),  # vector(1024) — handled via raw SQL
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    # pgvector index — use raw SQL since SQLAlchemy doesn't natively support ivfflat
    op.execute(
        "ALTER TABLE document_embeddings ALTER COLUMN embedding TYPE vector(1024)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_doc_embeddings_vector "
        "ON document_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    # ── audit_logs (for compliance & log retention) ─────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("details", JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # ── Helper function: minerals_near_point ────────────────────────────
    op.execute("""
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
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS minerals_near_point")
    op.drop_table("document_embeddings")
    op.drop_table("audit_logs")
    op.drop_table("observations")
    op.drop_table("mining_sites")
    op.drop_table("geochemical_samples")
    op.drop_table("structural_features")
    op.drop_table("mineral_occurrences")
    op.drop_table("geological_units")
    op.drop_table("rock_types")
    op.drop_table("users")
