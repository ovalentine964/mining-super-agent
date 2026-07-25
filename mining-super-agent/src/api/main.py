"""
Mining Super-Agent — FastAPI Application
Production-ready API with CORS, error handling, logging, and health checks.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.settings import get_settings
from src.db.database import close_db, init_db

logger = logging.getLogger("mining.api")
settings = get_settings()


# ── Request Logging Middleware ───────────────────────────────────
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with timing, status, and request ID."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()

        # Attach request ID for downstream use
        request.state.request_id = request_id

        # Sanitize path for logging (strip query params with potential secrets)
        path = request.url.path

        logger.info(
            "→ %s %s [%s]",
            request.method,
            path,
            request_id,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": path,
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", ""),
            },
        )

        try:
            response: Response = await call_next(request)
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            logger.exception(
                "✗ %s %s [%s] %.1fms UNHANDLED",
                request.method,
                path,
                request_id,
                elapsed,
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "request_id": request_id},
            )

        elapsed = (time.perf_counter() - start) * 1000
        logger.info(
            "← %s %s [%s] %d %.1fms",
            request.method,
            path,
            request_id,
            response.status_code,
            elapsed,
        )

        response.headers["X-Request-ID"] = request_id
        return response


# ── Error Handling Middleware ────────────────────────────────────
class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handler that returns structured JSON errors."""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.exception("Unhandled exception [%s]", request_id)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "detail": "An unexpected error occurred.",
                    "request_id": request_id,
                },
            )


# ── Lifespan ────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Startup
    logger.info("Starting Mining Super-Agent API (env=%s)", settings.app_env.value)
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down Mining Super-Agent API")
    await close_db()
    logger.info("Database connections closed")


# ── Application ─────────────────────────────────────────────────
app = FastAPI(
    title="Mining Super-Agent API",
    description="AI-powered mining intelligence for Kenya's artisanal miners",
    version="1.0.0",
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url="/api/redoc" if not settings.is_production else None,
    openapi_url="/api/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)

# ── Middleware (order matters: last added = first executed) ──────
# 1. CORS — must be first for preflight requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "Accept",
        "Origin",
        "User-Agent",
    ],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    max_age=600,  # Cache preflight for 10 minutes
)

# 2. Error handling
app.add_middleware(ErrorHandlingMiddleware)

# 3. Request logging (outermost = runs first)
app.add_middleware(RequestLoggingMiddleware)


# ── Route Registration ──────────────────────────────────────────
from src.api.routes.health import router as health_router      # noqa: E402
from src.api.routes.auth import router as auth_router          # noqa: E402

app.include_router(health_router, tags=["Health"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])


# ── Root Endpoint ───────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": "Mining Super-Agent API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/health",
    }


# ── API Version Info ────────────────────────────────────────────
@app.get("/api/v1", include_in_schema=False)
async def api_version_info():
    return {
        "version": "v1",
        "endpoints": {
            "health": "/health",
            "auth": "/api/v1/auth",
            "docs": "/api/docs",
        },
    }
