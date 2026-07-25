"""
Security middleware — SQL injection, XSS, and path traversal detection.
"""

from __future__ import annotations

import html
import logging
import re
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Patterns
SQL_INJECTION = [
    re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC|UNION|TRUNCATE)\b\s)", re.I),
    re.compile(r"(--|#|/\*|\*/)", re.I),
    re.compile(r"(\b(OR|AND)\b\s+\d+\s*=\s*\d+)", re.I),
    re.compile(r"(\bSLEEP\s*\(|\bBENCHMARK\s*\(|\bWAITFOR\s+DELAY\b)", re.I),
]

XSS_PATTERNS = [
    re.compile(r"<\s*script\b", re.I),
    re.compile(r"javascript\s*:", re.I),
    re.compile(r"on\w+\s*=", re.I),
]

PATH_TRAVERSAL = [
    re.compile(r"\.\./"),
    re.compile(r"%2[eE]%2[eE]"),
]


class SecurityMiddleware(BaseHTTPMiddleware):
    """Detects and blocks common web attacks."""

    SKIP_PATHS = {"/health", "/health/detailed", "/docs", "/openapi.json"}

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if any(path.startswith(p) for p in self.SKIP_PATHS):
            return await call_next(request)

        # Path traversal
        for p in PATH_TRAVERSAL:
            if p.search(path):
                logger.warning("Path traversal: %s from %s", path, request.client.host)
                return JSONResponse(status_code=400, content={"detail": "Invalid path"})

        # Query params
        for key, val in request.query_params.items():
            for p in SQL_INJECTION + XSS_PATTERNS:
                if p.search(val):
                    logger.warning("Injection in param '%s' from %s", key, request.client.host)
                    return JSONResponse(status_code=400, content={"detail": "Invalid parameter"})

        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response
