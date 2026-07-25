"""
Mining Super-Agent — Rate Limiting Middleware
Token bucket algorithm with Redis backend, per-user limits, 429 + Retry-After.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

import redis.asyncio as aioredis
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Rate Limit Tiers ────────────────────────────────────────────
# Requests per window (in seconds)
RATE_LIMIT_TIERS: dict[str, dict[str, int]] = {
    "anonymous": {"requests": 30, "window": 60},       # 30 req/min
    "authenticated": {"requests": 120, "window": 60},   # 120 req/min
    "premium": {"requests": 300, "window": 60},          # 300 req/min
    "admin": {"requests": 1000, "window": 60},           # 1000 req/min
    # Endpoint-specific overrides
    "auth_login": {"requests": 5, "window": 60},         # 5 login attempts/min
    "auth_register": {"requests": 3, "window": 300},     # 3 registrations/5min
}

# Paths that use stricter auth-specific limits
AUTH_PATHS = {
    "/api/v1/auth/login": "auth_login",
    "/api/v1/auth/register": "auth_register",
}


class TokenBucket:
    """Token bucket rate limiter backed by Redis.

    Uses Redis Lua script for atomic bucket operations.
    Each bucket has a capacity (max tokens) and refill rate.
    """

    # Lua script for atomic token bucket check-and-decrement
    LUA_SCRIPT = """
    local key = KEYS[1]
    local capacity = tonumber(ARGV[1])
    local refill_rate = tonumber(ARGV[2])
    local now = tonumber(ARGV[3])
    local requested = tonumber(ARGV[4])

    -- Get current bucket state
    local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
    local tokens = tonumber(bucket[1]) or capacity
    local last_refill = tonumber(bucket[2]) or now

    -- Calculate refill
    local elapsed = now - last_refill
    local new_tokens = elapsed * refill_rate
    tokens = math.min(capacity, tokens + new_tokens)

    -- Check if request can be served
    local allowed = 0
    local remaining = tokens
    if tokens >= requested then
        allowed = 1
        tokens = tokens - requested
        remaining = tokens
    end

    -- Update bucket state
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    redis.call('EXPIRE', key, math.ceil(capacity / refill_rate) * 2)

    return {allowed, remaining, capacity}
    """

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        self._script_sha: str | None = None

    async def _ensure_script(self) -> str:
        """Load Lua script into Redis and cache SHA."""
        if self._script_sha is None:
            self._script_sha = await self.redis.script_load(self.LUA_SCRIPT)
        return self._script_sha

    async def check(
        self,
        key: str,
        capacity: int,
        window: int,
        tokens: int = 1,
    ) -> tuple[bool, int, int]:
        """Check if request is allowed.

        Returns:
            (allowed, remaining, limit)
        """
        refill_rate = capacity / window  # tokens per second
        now = time.time()

        sha = await self._ensure_script()
        try:
            result = await self.redis.evalsha(
                sha,
                1,  # number of keys
                key,
                str(capacity),
                str(refill_rate),
                str(now),
                str(tokens),
            )
            allowed = bool(result[0])
            remaining = int(result[1])
            limit = int(result[2])
            return allowed, remaining, limit
        except aioredis.exceptions.NoScriptError:
            # Script expired from cache, reload
            self._script_sha = None
            return await self.check(key, capacity, window, tokens)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for per-user/IP rate limiting.

    Uses token bucket algorithm with Redis backend.
    Returns 429 with Retry-After header when limit exceeded.
    """

    def __init__(self, app, redis_url: str | None = None):
        super().__init__(app)
        self.redis_url = redis_url or settings.full_redis_url
        self._redis: aioredis.Redis | None = None
        self._bucket: TokenBucket | None = None

    async def _get_bucket(self) -> TokenBucket:
        """Lazy Redis connection."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=2,
                socket_connect_timeout=2,
            )
            self._bucket = TokenBucket(self._redis)
        return self._bucket

    def _get_identifier(self, request: Request) -> tuple[str, str]:
        """Get rate limit key and tier for the request.

        Returns (redis_key, tier_name).
        """
        # Check for authenticated user
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            # Extract user ID from JWT (lightweight decode)
            try:
                import jwt as pyjwt

                token = auth_header[7:]
                payload = pyjwt.decode(
                    token,
                    options={"verify_signature": False},
                )
                user_id = payload.get("sub", "unknown")
                tier = "authenticated"  # Could be premium/admin based on user lookup
                key = f"rl:user:{user_id}"
                return key, tier
            except Exception:
                pass

        # Fallback to IP-based limiting
        client_ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        return f"rl:ip:{client_ip}", "anonymous"

    def _get_retry_after(self, window: int) -> int:
        """Calculate seconds until next token is available."""
        return max(1, window // 10)  # At least 1 second, ~10% of window

    async def dispatch(self, request: Request, call_next) -> Response:
        """Apply rate limiting to the request."""
        # Skip rate limiting for health checks
        if request.url.path.startswith("/health"):
            return await call_next(request)

        bucket = await self._get_bucket()

        # Determine rate limit tier
        path = request.url.path
        tier_name = AUTH_PATHS.get(path, None)

        identifier, user_tier = self._get_identifier(request)
        if tier_name is None:
            tier_name = user_tier

        tier = RATE_LIMIT_TIERS.get(tier_name, RATE_LIMIT_TIERS["anonymous"])
        key = f"{identifier}:{tier_name}"

        # Check rate limit
        allowed, remaining, limit = await bucket.check(
            key=key,
            capacity=tier["requests"],
            window=tier["window"],
        )

        if not allowed:
            retry_after = self._get_retry_after(tier["window"])
            logger.warning(
                "Rate limit exceeded: %s (%s) on %s",
                identifier,
                tier_name,
                path,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "detail": f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + retry_after),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(
            int(time.time()) + tier["window"]
        )

        return response
