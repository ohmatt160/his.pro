"""
Security middleware for response headers and low-cost request validation.
"""

import logging
import os
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.utils.validators import Validators

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add browser security headers to every response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'")

        if request.url.scheme == "https" or os.getenv("APP_ENV") == "production":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        return response


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Reject obvious injection probes before they reach route handlers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        for key, value in request.query_params.multi_items():
            if Validators.contains_suspicious_input(value):
                logger.warning(
                    "Rejected suspicious query parameter %s on %s",
                    key,
                    request.url.path,
                )
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid request input"},
                )

        return await call_next(request)
