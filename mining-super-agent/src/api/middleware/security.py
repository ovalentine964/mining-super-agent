"""
Mining Super-Agent — Security Middleware
Input validation, SQL injection prevention, XSS prevention, request size limits.
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

# ── Patterns ────────────────────────────────────────────────────
# SQL injection patterns (case-insensitive)
SQL_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC|EXECUTE|UNION|TRUNCATE)\b\s)", re.I),
    re.compile(r"(--|#|/\*|\*/)", re.I),
    re.compile(r"(\b(OR|AND)\b\s+\d+\s*=\s*\d+)", re.I),
    re.compile(r"(';|\";\s*(SELECT|INSERT|UPDATE|DELETE|DROP))", re.I),
    re.compile(r"(\bSLEEP\s*\(|\bBENCHMARK\s*\(|\bWAITFOR\s+DELAY\b)", re.I),
    re.compile(r"(\bINTO\s+(OUT|DUMP)FILE\b)", re.I),
    re.compile(r"(\bLOAD_FILE\s*\(|\bLOAD_DATA\b)", re.I),
]

# XSS patterns
XSS_PATTERNS: list[re.Pattern] = [
    re.compile(r"<\s*script\b", re.I),
    re.compile(r"javascript\s*:", re.I),
    re.compile(r"on\w+\s*=", re.I),
    re.compile(r"<\s*iframe\b", re.I),
    re.compile(r"<\s*object\b", re.I),
    re.compile(r"<\s*embed\b", re.I),
    re.compile(r"<\s*form\b", re.I),
    re.compile(r"data\s*:\s*text/html", re.I),
    re.compile(r"vbscript\s*:", re.I),
]

# Path traversal patterns
PATH_TRAVERSAL_PATTERNS: list[re.Pattern] = [
    re.compile(r"\.\./"),
    re.compile(r"\.\.%2[fF]"),
    re.compile(r"%2[eE]%2[eE]"),
]

# Maximum sizes
MAX_URL_LENGTH = 2048
MAX_HEADER_VALUE_LENGTH = 8192
MAX_BODY_SIZE = 10 * 1024 * 1024  # 10MB


def _check_sql_injection(value: str) -> bool:
    """Check if a string contains SQL injection patterns."""
    for pattern in SQL_INJECTION_PATTERNS:
        if pattern.search(value):
            return True
    return False


def _check_xss(value: str) -> bool:
    """Check if a string contains XSS patterns."""
    for pattern in XSS_PATTERNS:
        if pattern.search(value):
            return True
    return False


def _check_path_traversal(value: str) -> bool:
    """Check if a string contains path traversal patterns."""
    for pattern in PATH_TRAVERSAL_PATTERNS:
        if pattern.search(value):
            return True
    return False


def _sanitize_string(value: str) -> str:
    """Sanitize a string by HTML-encoding special characters."""
    return html.escape(value, quote=True)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware.

    Checks:
    - Request size limits
    - URL length limits
    - SQL injection in query params, headers, and body
    - XSS in query params and body
    - Path traversal in URL
    - Suspicious header values
    """

    # Paths that skip security checks (health, docs)
    SKIP_PATHS: set[str] = {"/health", "/health/detailed", "/docs", "/openapi.json"}

    # Paths that accept JSON bodies (skip body check for others)
    JSON_PATHS: set[str] = {"/api/"}

    async def dispatch(self, request: Request, call_next) -> Response:
        """Apply security checks to every request."""
        path = request.url.path

        # Skip static/health paths
        if any(path.startswith(skip) for skip in self.SKIP_PATHS):
            return await call_next(request)

        # 1. URL length check
        if len(str(request.url)) > MAX_URL_LENGTH:
            logger.warning("URL too long: %d chars from %s", len(str(request.url)), request.client.host)
            return JSONResponse(
                status_code=414,
                content={"error": "uri_too_long", "detail": "URL exceeds maximum length"},
            )

        # 2. Path traversal check
        if _check_path_traversal(path):
            logger.warning("Path traversal attempt: %s from %s", path, request.client.host)
            return JSONResponse(
                status_code=400,
                content={"error": "bad_request", "detail": "Invalid path"},
            )

        # 3. Query parameter checks
        for key, value in request.query_params.items():
            if _check_sql_injection(value):
                logger.warning(
                    "SQL injection attempt in query param '%s': %.100s from %s",
                    key, value, request.client.host,
                )
                return JSONResponse(
                    status_code=400,
                    content={"error": "bad_request", "detail": "Invalid query parameter"},
                )
            if _check_xss(value):
                logger.warning(
                    "XSS attempt in query param '%s': %.100s from %s",
                    key, value, request.client.host,
                )
                return JSONResponse(
                    status_code=400,
                    content={"error": "bad_request", "detail": "Invalid query parameter"},
                )

        # 4. Header checks
        for header_name in ("user-agent", "referer", "x-forwarded-for"):
            header_value = request.headers.get(header_name, "")
            if len(header_value) > MAX_HEADER_VALUE_LENGTH:
                logger.warning("Oversized header: %s (%d chars)", header_name, len(header_value))
                return JSONResponse(
                    status_code=400,
                    content={"error": "bad_request", "detail": "Invalid header"},
                )
            if _check_sql_injection(header_value):
                logger.warning("SQL injection in header '%s' from %s", header_name, request.client.host)
                return JSONResponse(
                    status_code=400,
                    content={"error": "bad_request", "detail": "Invalid header"},
                )

        # 5. Body checks (for JSON endpoints)
        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                # Read body
                body = await request.body()

                # Size check
                if len(body) > MAX_BODY_SIZE:
                    logger.warning("Body too large: %d bytes from %s", len(body), request.client.host)
                    return JSONResponse(
                        status_code=413,
                        content={"error": "payload_too_large", "detail": "Request body exceeds 10MB limit"},
                    )

                # Content check (scan raw body for injection patterns)
                try:
                    body_str = body.decode("utf-8", errors="ignore")
                    if _check_sql_injection(body_str):
                        logger.warning("SQL injection in body from %s", request.client.host)
                        return JSONResponse(
                            status_code=400,
                            content={"error": "bad_request", "detail": "Invalid request body"},
                        )
                    if _check_xss(body_str):
                        logger.warning("XSS in body from %s", request.client.host)
                        return JSONResponse(
                            status_code=400,
                            content={"error": "bad_request", "detail": "Invalid request body"},
                        )
                except Exception:
                    pass  # Binary body, skip content check

        # 6. All checks passed — process request
        response = await call_next(request)

        # Add security headers (defense in depth — Caddy also sets these)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response
