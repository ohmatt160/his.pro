"""
Security middleware for response headers and low-cost request validation.
"""

import logging
import os
import hmac
import hashlib
import secrets
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.utils.validators import Validators

logger = logging.getLogger(__name__)

CSRF_COOKIE_NAME = "hispro_csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _csrf_secret() -> bytes:
    secret = os.getenv("CSRF_SECRET_KEY") or os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET_KEY") or ""
    if not secret:
        secret = "development-csrf-secret"
    return secret.encode("utf-8")


def create_csrf_token() -> str:
    nonce = secrets.token_urlsafe(32)
    signature = hmac.new(_csrf_secret(), nonce.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{nonce}.{signature}"


def valid_csrf_token(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    nonce, signature = token.rsplit(".", 1)
    if not nonce or not signature:
        return False
    expected = hmac.new(_csrf_secret(), nonce.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


def set_csrf_cookie(response: Response) -> None:
    secure = os.getenv("APP_ENV") == "production" or os.getenv("COOKIE_SECURE", "").lower() == "true"
    response.set_cookie(
        CSRF_COOKIE_NAME,
        create_csrf_token(),
        max_age=int(os.getenv("CSRF_TOKEN_EXPIRES", str(7 * 24 * 3600))),
        httponly=False,
        secure=secure,
        samesite="none" if secure else "lax",
        path="/",
    )


def clear_csrf_cookie(response: Response) -> None:
    secure = os.getenv("APP_ENV") == "production" or os.getenv("COOKIE_SECURE", "").lower() == "true"
    response.delete_cookie(CSRF_COOKIE_NAME, path="/", secure=secure, samesite="none" if secure else "lax")


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


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit CSRF protection for cookie-authenticated unsafe requests."""

    def __init__(self, app, exempt_paths: list[str] | None = None):
        super().__init__(app)
        self.exempt_paths = set(exempt_paths or [
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/ensure",
        ])

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if (
            request.method not in UNSAFE_METHODS
            or request.method == "OPTIONS"
            or request.url.path in self.exempt_paths
        ):
            return await call_next(request)

        uses_cookie_auth = bool(
            request.cookies.get("hispro_access_token")
            or request.cookies.get("hispro_refresh_token")
        )
        if not uses_cookie_auth:
            return await call_next(request)
        if not request.headers.get("origin") and not request.headers.get("referer"):
            return await call_next(request)

        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
        header_token = request.headers.get(CSRF_HEADER_NAME)
        if not cookie_token or not header_token:
            return JSONResponse(status_code=403, content={"detail": "CSRF token required"})
        if not hmac.compare_digest(cookie_token, header_token) or not valid_csrf_token(cookie_token):
            logger.warning("Rejected CSRF validation failure on %s", request.url.path)
            return JSONResponse(status_code=403, content={"detail": "CSRF validation failed"})

        return await call_next(request)


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
