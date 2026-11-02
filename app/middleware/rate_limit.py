"""
Rate limiting middleware for FastAPI.

Auth-sensitive endpoints get explicit per-IP windows and all limited responses
include Retry-After plus rate-limit headers.
"""

import asyncio
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Callable

import redis
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.utils.network import client_ip

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitRule:
    limit: int
    window_seconds: int


AUTH_ENDPOINT_LIMITS = {
    ("POST", "/api/v1/auth/login"): RateLimitRule(5, 60),
    ("POST", "/api/v1/auth/register"): RateLimitRule(3, 60),
    ("POST", "/api/v1/auth/ensure"): RateLimitRule(3, 60),
    ("POST", "/api/v1/auth/onboard"): RateLimitRule(3, 60),
    ("POST", "/api/v1/auth/verify"): RateLimitRule(5, 60),
    ("POST", "/api/v1/password-reset/forgot"): RateLimitRule(3, 60),
    ("POST", "/api/v1/password-reset/confirm"): RateLimitRule(5, 60),
}

DEFAULT_API_LIMIT = RateLimitRule(120, 60)
UPLOAD_LIMIT = RateLimitRule(20, 60)
SEARCH_LIMIT = RateLimitRule(30, 60)

_memory_windows: dict[str, tuple[int, float]] = {}
_redis_client_instance = None
_redis_client_url: str | None = None
_redis_client_lock = threading.Lock()
_INCREMENT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {count, ttl}
"""


def get_client_ip(request: Request) -> str:
    return client_ip(request)


def get_rate_limit_key(request: Request) -> str:
    return get_client_ip(request)


def _rule_for_request(request: Request) -> RateLimitRule:
    method_path = (request.method.upper(), request.url.path)
    if method_path in AUTH_ENDPOINT_LIMITS:
        return AUTH_ENDPOINT_LIMITS[method_path]
    if request.url.path.startswith("/api/v1/files/"):
        return UPLOAD_LIMIT
    if "search" in request.query_params or "/search" in request.url.path:
        return SEARCH_LIMIT
    return DEFAULT_API_LIMIT


def _redis_client():
    global _redis_client_instance, _redis_client_url
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        return None
    with _redis_client_lock:
        if _redis_client_instance is None or _redis_client_url != redis_url:
            if _redis_client_instance is not None:
                _redis_client_instance.close()
            _redis_client_instance = redis.from_url(
                redis_url,
                socket_connect_timeout=0.2,
                socket_timeout=0.2,
            )
            _redis_client_url = redis_url
        return _redis_client_instance


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window rate limiter with Redis and in-memory fallback."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method == "OPTIONS" or request.url.path in {"/health", "/docs", "/redoc", "/openapi.json"}:
            return await call_next(request)

        rule = _rule_for_request(request)
        namespace = os.getenv("RATE_LIMIT_NAMESPACE", "hispro")
        key = f"{namespace}:rate:{request.method}:{request.url.path}:{get_rate_limit_key(request)}"
        if os.getenv("REDIS_URL", "").strip():
            count, reset_at = await asyncio.to_thread(self._increment, key, rule)
        else:
            count, reset_at = self._increment(key, rule)
        remaining = max(rule.limit - count, 0)
        retry_after = max(int(reset_at - time.time()), 1)

        if count > rule.limit:
            logger.warning("Rate limit exceeded for %s", key)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(rule.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(reset_at)),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(rule.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_at))
        return response

    def _increment(self, key: str, rule: RateLimitRule) -> tuple[int, float]:
        now = time.time()

        client = _redis_client()
        if client:
            try:
                current, ttl = client.eval(_INCREMENT_SCRIPT, 1, key, rule.window_seconds)
                reset_at = now + (ttl if ttl > 0 else rule.window_seconds)
                return int(current), reset_at
            except redis.RedisError as exc:
                logger.warning("Redis unavailable for rate limiting: %s", exc)

        count, reset_at = _memory_windows.get(key, (0, now + rule.window_seconds))
        if reset_at <= now:
            count = 0
            reset_at = now + rule.window_seconds

        count += 1
        _memory_windows[key] = (count, reset_at)
        return count, reset_at


def init_rate_limiter(app):
    return None


def rate_limit_by_user(limit_string: str):
    def decorator(func):
        return func
    return decorator


def rate_limit_by_ip(limit_string: str):
    def decorator(func):
        return func
    return decorator


AUTH_RATE_LIMIT = "5 per minute"
API_RATE_LIMIT = "120 per minute"
UPLOAD_RATE_LIMIT = "20 per minute"
SEARCH_RATE_LIMIT = "30 per minute"
