"""
Database models — SQLAlchemy ORM with PostGIS geometry types.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry

from src.db.database import Base
from src.db.encryption import EncryptedString


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(30))
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(EncryptedString(512))
    mfa_backup_codes: Mapped[Optional[list]] = mapped_column(JSONB)
    max_concurrent_sessions: Mapped[int] = mapped_column(Integer, default=5)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(45))
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    observations: Mapped[list["Observation"]] = relationship(back_populates="user", lazy="selectin")


class GeologicalUnit(Base):
    __tablename__ = "geological_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    age: Mapped[Optional[str]] = mapped_column(String(100))
    rock_type: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[Optional[str]] = mapped_column(String(100))
    properties: Mapped[Optional[dict]] = mapped_column(JSONB)
    geom: Mapped[Optional[str]] = mapped_column(Geometry(geometry_type="MULTIPOLYGON", srid=4326))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    mineral_occurrences: Mapped[list["MineralOccurrence"]] = relationship(back_populates="geological_unit", lazy="selectin")


class MineralOccurrence(Base):
    __tablename__ = "mineral_occurrences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mineral: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    grade: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    grade_unit: Mapped[Optional[str]] = mapped_column(String(20))
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    geological_unit_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("geological_units.id"))
    properties: Mapped[Optional[dict]] = mapped_column(JSONB)
    geom: Mapped[Optional[str]] = mapped_column(Geometry(geometry_type="POINT", srid=4326))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    geological_unit: Mapped[Optional[GeologicalUnit]] = relationship(back_populates="mineral_occurrences")
    observations: Mapped[list["Observation"]] = relationship(back_populates="mineral_occurrence", lazy="selectin")


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    mineral_occurrence_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("mineral_occurrences.id"))
    title: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    photo_urls: Mapped[Optional[list]] = mapped_column(JSONB)
    rock_type: Mapped[Optional[str]] = mapped_column(String(100))
    color: Mapped[Optional[str]] = mapped_column(String(50))
    luster: Mapped[Optional[str]] = mapped_column(String(50))
    hardness: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2))
    xrf_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    ai_analysis: Mapped[Optional[dict]] = mapped_column(JSONB)
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    geom: Mapped[Optional[str]] = mapped_column(Geometry(geometry_type="POINT", srid=4326))
    client_id: Mapped[Optional[str]] = mapped_column(String(36))
    synced: Mapped[bool] = mapped_column(Boolean, default=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="observations")
    mineral_occurrence: Mapped[Optional[MineralOccurrence]] = relationship(back_populates="observations")


class RockType(Base):
    __tablename__ = "rock_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    classification: Mapped[Optional[str]] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(Text)
    properties: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
