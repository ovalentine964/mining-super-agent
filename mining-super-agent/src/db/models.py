"""
Mining Super-Agent — SQLAlchemy ORM Models
PostGIS geometry types for spatial queries.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# GeoAlchemy2 for PostGIS geometry columns
from geoalchemy2 import Geometry

from src.db.database import Base


# ── Geological Units ────────────────────────────────────────────
class GeologicalUnit(Base):
    """Geological formation/unit with spatial extent.

    Represents a mapped geological unit (e.g., Nyanzian Greenstone Belt,
    Kisii Group) with its polygon boundary and metadata.
    """

    __tablename__ = "geological_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    age: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rock_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    properties: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # PostGIS geometry — MultiPolygon in WGS84
    geom: Mapped[Optional[str]] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    mineral_occurrences: Mapped[list["MineralOccurrence"]] = relationship(
        back_populates="geological_unit", lazy="selectin"
    )

    __table_args__ = (
        Index("idx_geological_units_geom", "geom", postgresql_using="gist"),
        Index("idx_geological_units_rock_type", "rock_type"),
    )


# ── Mineral Occurrences ────────────────────────────────────────
class MineralOccurrence(Base):
    """Recorded mineral occurrence at a specific location.

    Stores point locations where minerals have been identified,
    along with grade, confidence, and source information.
    """

    __tablename__ = "mineral_occurrences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mineral: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    grade: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    grade_unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True)
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        description="Data source: observation, model, survey, literature"
    )
    geological_unit_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("geological_units.id"), nullable=True
    )
    properties: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # PostGIS geometry — Point in WGS84
    geom: Mapped[Optional[str]] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    geological_unit: Mapped[Optional[GeologicalUnit]] = relationship(
        back_populates="mineral_occurrences"
    )
    observations: Mapped[list["Observation"]] = relationship(
        back_populates="mineral_occurrence", lazy="selectin"
    )

    __table_args__ = (
        Index("idx_mineral_occurrences_geom", "geom", postgresql_using="gist"),
        Index("idx_mineral_occurrences_mineral", "mineral"),
        Index("idx_mineral_occurrences_source", "source"),
        Index("idx_mineral_occurrences_recorded", "recorded_at"),
    )


# ── Observations ────────────────────────────────────────────────
class Observation(Base):
    """User-submitted field observation (photos, notes, measurements).

    Links to a mineral occurrence when the observation identifies minerals.
    Supports offline-first: observations sync from mobile app.
    """

    __tablename__ = "observations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    mineral_occurrence_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("mineral_occurrences.id"), nullable=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photo_urls: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    rock_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    luster: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    hardness: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2), nullable=True)
    xrf_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ai_analysis: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True)

    # PostGIS geometry — Point in WGS84
    geom: Mapped[Optional[str]] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
    )

    # Offline sync support
    client_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True,
        description="Client-generated UUID for offline dedup"
    )
    synced: Mapped[bool] = mapped_column(Boolean, default=True)

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="observations")
    mineral_occurrence: Mapped[Optional[MineralOccurrence]] = relationship(
        back_populates="observations"
    )

    __table_args__ = (
        Index("idx_observations_geom", "geom", postgresql_using="gist"),
        Index("idx_observations_user", "user_id"),
        Index("idx_observations_client_id", "client_id", unique=True),
        Index("idx_observations_observed_at", "observed_at"),
    )


# ── Users ───────────────────────────────────────────────────────
class User(Base):
    """User account with authentication and profile data.

    Supports TOTP-based MFA and multiple API keys.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    preferred_language: Mapped[str] = mapped_column(
        String(10), default="en",
        description="en | sw | luo | kam | lux"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # MFA (TOTP)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    mfa_backup_codes: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Session tracking
    max_concurrent_sessions: Mapped[int] = mapped_column(Integer, default=5)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    observations: Mapped[list[Observation]] = relationship(
        back_populates="user", lazy="selectin"
    )
    api_keys: Mapped[list["ApiKey"]] = relationship(
        back_populates="user", lazy="selectin"
    )

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_username", "username"),
    )


# ── API Keys ────────────────────────────────────────────────────
class ApiKey(Base):
    """Encrypted API key storage for external services.

    Keys are encrypted at rest using Fernet symmetric encryption.
    Each key is scoped to a specific service (nvidia, groq, etc.).
    """

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    service: Mapped[str] = mapped_column(
        String(50), nullable=False,
        description="Service name: nvidia, groq, google_ai, together, mistral"
    )
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    key_hint: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        description="Last 4 chars of the key for display"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    rate_limit_remaining: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    rate_limit_reset_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped[User] = relationship(back_populates="api_keys")

    __table_args__ = (
        Index("idx_api_keys_user_service", "user_id", "service"),
        Index("idx_api_keys_service_active", "service", "is_active"),
    )
