"""
Health check endpoints for monitoring and load balancers.
"""

from __future__ import annotations

import asyncio
import logging
import time

import redis.asyncio as aioredis
from fastapi import APIRouter
from sqlalchemy import text

from src.config.settings import get_settings
from src.db.database import engine

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


@router.get("/health")
async def health():
    """Basic health check — returns 200 if the app is running."""
    return {"status": "healthy", "service": "mining-super-agent"}


@router.get("/health/detailed")
async def detailed_health():
    """Detailed health check — verifies database, Redis, and Qdrant."""
    results = {}
    start = time.perf_counter()

    # Check PostgreSQL
    async def _check_db():
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return {"status": "healthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    # Check Redis
    async def _check_redis():
        try:
            r = aioredis.from_url(settings.full_redis_url, socket_timeout=2)
            await r.ping()
            await r.aclose()
            return {"status": "healthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    # Check Qdrant
    async def _check_qdrant():
        try:
            import httpx
            async with httpx.AsyncClient(timeout=2) as client:
                resp = await client.get(f"{settings.qdrant_url}/healthz")
                if resp.status_code == 200:
                    return {"status": "healthy"}
            return {"status": "unhealthy", "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    db_result, redis_result, qdrant_result = await asyncio.gather(
        _check_db(),
        _check_redis(),
        _check_qdrant(),
    )

    elapsed_ms = (time.perf_counter() - start) * 1000
    all_healthy = all(
        r["status"] == "healthy"
        for r in [db_result, redis_result, qdrant_result]
    )

    return {
        "status": "healthy" if all_healthy else "degraded",
        "elapsed_ms": round(elapsed_ms, 1),
        "checks": {
            "database": db_result,
            "redis": redis_result,
            "qdrant": qdrant_result,
        },
    }
