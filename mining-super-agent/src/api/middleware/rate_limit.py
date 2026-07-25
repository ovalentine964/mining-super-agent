"""
Rate limiting middleware — Redis-backed token bucket.
"""

from __future__ import annotations

import logging
import time

import redis.asyncio as aioredis
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

RATE_LIMITS = {
    "default": {"requests": 60, "window": 60},
    "auth": {"requests": 5, "window": 60},
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP rate limiting with Redis backend."""

    def __init__(self, app, redis_url: str | None = None):
        super().__init__(app)
        self.redis_url = redis_url or settings.full_redis_url
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path.startswith("/health"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        tier = "auth" if "/auth/" in request.url.path else "default"
        limit = RATE_LIMITS[tier]
        key = f"rl:{tier}:{client_ip}"

        try:
            r = await self._get_redis()
            current = await r.incr(key)
            if current == 1:
                await r.expire(key, limit["window"])

            if current > limit["requests"]:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": str(limit["window"])},
                )

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(limit["requests"])
            response.headers["X-RateLimit-Remaining"] = str(max(0, limit["requests"] - current))
            return response
        except Exception as e:
            logger.warning("Rate limit error: %s", e)
            return await call_next(request)
