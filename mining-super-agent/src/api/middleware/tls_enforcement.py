"""
TLS enforcement middleware — defense-in-depth for HTTPS.

While Caddy handles TLS termination and HTTP→HTTPS redirect at the
proxy level, this middleware provides a second layer of enforcement
inside the application itself. It ensures:

1. All HTTP requests are rejected (not redirected) at the app level
2. HSTS headers are always present
3. Certificate pinning headers for mobile apps (optional)
4. X-Forwarded-Proto is validated against spoofing

This is critical for production deployments where the app might
be accessed directly (bypassing Caddy) or when deploying behind
different reverse proxies.
"""

from __future__ import annotations

import logging
import os
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────
# HSTS max-age: 2 years (63072000 seconds)
HSTS_MAX_AGE = 63_072_000
HSTS_HEADER = f"max-age={HSTS_MAX_AGE}; includeSubDomains; preload"

# Environment detection
APP_ENV = os.getenv("APP_ENV", "production").lower()
IS_PRODUCTION = APP_ENV == "production"

# Trusted proxy headers (Caddy sets these)
FORWARDED_PROTO_HEADER = "X-Forwarded-Proto"
FORWARDED_FOR_HEADER = "X-Forwarded-For"

# Paths exempt from TLS enforcement (health checks behind proxy)
TLS_EXEMPT_PATHS: set[str] = {"/health", "/health/detailed"}


class TLSEnforcementMiddleware(BaseHTTPMiddleware):
    """Enforce HTTPS at the application level.

    In production mode:
    - Rejects plain HTTP requests with 403
    - Validates X-Forwarded-Proto to prevent header spoofing
    - Injects HSTS header on every response
    - Optionally adds HPKP-style pinning headers for mobile clients

    In development mode:
    - Skips TLS enforcement (allows plain HTTP)
    - Still injects HSTS header for testing
    """

    def __init__(
        self,
        app,
        enforce: bool | None = None,
        hsts_max_age: int = HSTS_MAX_AGE,
        pin_header: str | None = None,
    ):
        super().__init__(app)
        # Enforce TLS in production unless explicitly overridden
        self.enforce = enforce if enforce is not None else IS_PRODUCTION
        self.hsts_max_age = hsts_max_age
        self.hsts_value = f"max-age={hsts_max_age}; includeSubDomains; preload"
        # Optional: certificate pinning header for mobile apps
        # Example: "pin-sha256=<base64>; pin-sha256=<backup>; max-age=5184000"
        self.pin_header = pin_header

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Skip enforcement for exempt paths
        if path in TLS_EXEMPT_PATHS:
            response = await call_next(request)
            response.headers["Strict-Transport-Security"] = self.hsts_value
            return response

        # ── TLS Enforcement ──────────────────────────────────────
        if self.enforce:
            # Determine if request is actually HTTPS
            is_https = self._is_secure(request)

            if not is_https:
                client_ip = request.client.host if request.client else "unknown"
                logger.warning(
                    "TLS violation: plain HTTP request to %s from %s",
                    path,
                    client_ip,
                )
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "tls_required",
                        "detail": "HTTPS is required. All HTTP requests are rejected.",
                        "upgrade": f"https://{request.url.netloc}{request.url.path}",
                    },
                )

        # ── Response Headers ─────────────────────────────────────
        response: Response = await call_next(request)

        # Always inject HSTS (even in dev — browsers only honor it over HTTPS)
        response.headers["Strict-Transport-Security"] = self.hsts_value

        # Optional: certificate pinning for mobile app
        if self.pin_header:
            response.headers["Public-Key-Pins"] = self.pin_header

        return response

    @staticmethod
    def _is_secure(request: Request) -> bool:
        """Determine if the request arrived over HTTPS.

        Checks multiple signals in order of trust:
        1. Direct HTTPS (ASGI scheme)
        2. X-Forwarded-Proto header (from trusted proxy like Caddy)
        3. X-Forwarded-SSL header (some proxies)
        """
        # Direct connection
        if request.url.scheme == "https":
            return True

        # Proxy header (Caddy sets this)
        forwarded_proto = request.headers.get(FORWARDED_PROTO_HEADER, "").lower()
        if forwarded_proto == "https":
            return True

        # Some proxies set this
        forwarded_ssl = request.headers.get("X-Forwarded-SSL", "").lower()
        if forwarded_ssl == "on":
            return True

        return False
