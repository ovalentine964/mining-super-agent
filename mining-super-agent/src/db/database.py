"""
Database setup — Async SQLAlchemy with PostGIS.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class Base(DeclarativeBase):
    pass


engine: AsyncEngine = create_async_engine(
    settings.async_database_url,
    echo=settings.debug,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    connect_args={
        "server_settings": {"application_name": "mining-super-agent", "jit": "off"},
        "command_timeout": 30,
    },
)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False,
)


@event.listens_for(engine.sync_engine, "connect")
def _set_postgis_search_path(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("SET search_path TO public, topology, tiger;")
    cursor.close()


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
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
    async with get_session() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis_topology;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        logger.info("Database extensions initialized")


async def check_db_health() -> dict[str, str]:
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version();"))
            return {"status": "healthy", "version": result.scalar_one()}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def close_db() -> None:
    await engine.dispose()
    logger.info("Database connection pool disposed")
