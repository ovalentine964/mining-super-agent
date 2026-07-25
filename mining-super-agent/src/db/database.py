"""
Mining Super-Agent — Async SQLAlchemy Database Setup
PostgreSQL + PostGIS with connection pooling and session management.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ── Engine ───────────────────────────────────────────────────────
# Connection pool sized for Oracle Cloud free tier (4 cores, 24GB RAM)
# Pool: 5 base connections, 10 overflow, 30s timeout
engine: AsyncEngine = create_async_engine(
    settings.async_database_url,
    echo=settings.debug,
    echo_pool=settings.debug,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,       # Recycle connections every 30 min
    pool_pre_ping=True,      # Verify connections before use
    connect_args={
        "server_settings": {
            "application_name": "mining-super-agent",
            "jit": "off",  # Disable JIT for consistent performance
        },
        "command_timeout": 30,
    },
)

# Session factory — async sessions with expire_on_commit=False
# so objects remain accessible after commit
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── PostGIS Extension ───────────────────────────────────────────
@event.listens_for(engine.sync_engine, "connect")
def _set_postgis_search_path(dbapi_conn, connection_record):
    """Ensure PostGIS types are in the search path on each connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute("SET search_path TO public, topology, tiger;")
    cursor.close()


# ── Session Dependency ──────────────────────────────────────────
@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions with automatic rollback on error.

    Usage:
        async with get_session() as session:
            result = await session.execute(select(User))
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.

    Usage:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with get_session() as session:
        yield session


# ── Database Initialization ─────────────────────────────────────
async def init_db() -> None:
    """Initialize database extensions (PostGIS, pgvector).

    Call once at application startup.
    """
    async with engine.begin() as conn:
        # Enable PostGIS
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis_topology;"))
        # Enable pgvector for embeddings
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        # Enable trigram for text search
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        logger.info("Database extensions initialized: postgis, vector, pg_trgm")


async def check_db_health() -> dict[str, str]:
    """Check database connectivity. Returns status dict."""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version();"))
            version = result.scalar_one()
            return {"status": "healthy", "version": version}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


async def close_db() -> None:
    """Dispose of the engine connection pool. Call at shutdown."""
    await engine.dispose()
    logger.info("Database connection pool disposed")
