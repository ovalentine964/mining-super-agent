"""
Security headers middleware — defense-in-depth for the FastAPI application.

These headers are ALSO set at the Caddy reverse-proxy level, but we duplicate
them here so the app is secure even if Caddy is bypassed (direct port access,
development mode, or misconfigured proxy).
"""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# ── Security Header Constants ────────────────────────────────────
SECURITY_HEADERS: dict[str, str] = {
    # Enforce HTTPS for 2 years, include subdomains, eligible for HSTS preload
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    # Prevent clickjacking — never allow framing
    "X-Frame-Options": "DENY",
    # Prevent MIME-type sniffing
    "X-Content-Type-Options": "nosniff",
    # Legacy XSS filter (still useful for older browsers)
    "X-XSS-Protection": "1; mode=block",
    # Control referrer information sent to other origins
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # Content Security Policy — strict default, expand as needed
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    ),
    # Cross-origin isolation headers
    "Cross-Origin-Embedder-Policy": "require-corp",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    # Feature / permissions policy
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(self)",
}

# Headers to REMOVE (information leakage)
HEADERS_TO_REMOVE: list[str] = [
    "Server",
    "X-Powered-By",
    "X-AspNet-Version",
    "X-AspNetMvc-Version",
]


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject security headers into every response.

    This is a Starlette middleware that runs on every request and
    injects the full set of OWASP-recommended security headers.
    """

    def __init__(self, app, extra_headers: dict[str, str] | None = None):
        super().__init__(app)
        self.headers = {**SECURITY_HEADERS}
        if extra_headers:
            self.headers.update(extra_headers)

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # Inject security headers
        for header_name, header_value in self.headers.items():
            response.headers[header_name] = header_value

        # Remove information-leaking headers
        for header_name in HEADERS_TO_REMOVE:
            if header_name in response.headers:
                del response.headers[header_name]

        return response
