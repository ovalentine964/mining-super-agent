"""
Mining Super-Agent — Health Check Endpoints
Basic and detailed health checks for monitoring.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.config.settings import get_settings
from src.db.database import check_db_health

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


async def _check_redis() -> dict[str, str]:
    """Check Redis connectivity."""
    try:
        client = aioredis.from_url(
            settings.full_redis_url,
            socket_timeout=3,
            socket_connect_timeout=3,
        )
        await client.ping()
        info = await client.info("server")
        version = info.get("redis_version", "unknown")
        await client.aclose()
        return {"status": "healthy", "version": version}
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


async def _check_qdrant() -> dict[str, str]:
    """Check Qdrant connectivity."""
    try:
        import httpx

        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.qdrant_url}/healthz")
            if resp.status_code == 200:
                return {"status": "healthy"}
            return {"status": "unhealthy", "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        logger.warning(f"Qdrant health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


@router.get("/health")
async def health_basic():
    """Basic health check — returns 200 if the app is running."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/health/detailed")
async def health_detailed():
    """Detailed health check — verifies database, Redis, and Qdrant.

    Returns 200 only if ALL services are healthy.
    Returns 503 if any critical service is down.
    """
    db_result, redis_result, qdrant_result = await asyncio.gather(
        check_db_health(),
        _check_redis(),
        _check_qdrant(),
        return_exceptions=False,
    )

    services = {
        "database": db_result,
        "redis": redis_result,
        "qdrant": qdrant_result,
    }

    all_healthy = all(s.get("status") == "healthy" for s in services.values())

    result = {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": services,
        "version": "1.0.0",
        "environment": settings.app_env.value,
    }

    if all_healthy:
        return result
    return JSONResponse(status_code=503, content=result)
