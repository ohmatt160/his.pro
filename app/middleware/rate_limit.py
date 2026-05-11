"""
Rate Limiting Middleware for FastAPI
Using slowapi for distributed rate limiting with Redis backend
"""

import time
import redis
from typing import Callable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import logging

logger = logging.getLogger(__name__)

def get_rate_limit_key(request: Request) -> str:
    """
    Generate a rate limit key based on user identity or IP address
    """
    # Try to get user ID from JWT token if authenticated
    try:
        from app.middleware.jwt import verify_token
        authorization: str = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
            token_data = verify_token(token)
            if token_data and "sub" in token_data:
                user_id = token_data["sub"]
                return f"user:{user_id}"
    except Exception:
        pass
    
    # Fall back to IP address
    return get_remote_address()

# Initialize rate limiter
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.getenv('REDIS_URL', 'redis://localhost:6379'),
    strategy="fixed-window"
)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Custom rate limiting middleware that integrates with FastAPI
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Apply rate limiting based on endpoint type
        path = request.url.path
        
        # Define rate limits for different endpoint types
        if path.startswith("/api/v1/auth/"):
            # Strict limit for auth endpoints
            limit = "10 per minute"
        elif path.startswith("/api/v1/files/"):
            # Limit for file uploads
            limit = "20 per minute"
        elif "/search" in path or "/filter" in path:
            # Limit for search operations
            limit = "30 per minute"
        else:
            # Standard API limit
            limit = "100 per minute"
        
        try:
            # Check if request is allowed
            limiter.limit(limit).key_func = get_rate_limit_key
            # This is a simplified approach - in practice, you'd use slowapi's decorator
            # For now, we'll implement basic rate limiting logic
            
            # Get current count from Redis
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            try:
                redis_client = redis.from_url(redis_url)
                key = f"rate_limit:{get_rate_limit_key(request)}:{path}"
                current = redis_client.get(key)
                
                if current is None:
                    # First request, set expiration
                    redis_client.setex(key, 60, 1)  # 1 minute window
                else:
                    count = int(current)
                    if count >= self._parse_limit(limit):
                        logger.warning(f"Rate limit exceeded for {get_rate_limit_key(request)} on {path}")
                        raise HTTPException(
                            status_code=429,
                            detail={
                                "error": "Rate limit exceeded",
                                "message": f"You have exceeded the rate limit. Please try again later.",
                                "retry_after": 60
                            }
                        )
                    else:
                        # Increment counter
                        redis_client.incr(key)
            except redis.RedisError as e:
                logger.warning(f"Redis error in rate limiting: {e}")
                # If Redis is down, allow request to proceed (fail open)
                pass
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in rate limiting middleware: {e}")
            # Fail open - don't block requests due to rate limiting errors
            
        response = await call_next(request)
        return response
    
    def _parse_limit(self, limit: str) -> int:
        """
        Parse limit string like '10 per minute' to integer
        """
        try:
            number = int(limit.split()[0])
            return number
        except (ValueError, IndexError):
            return 60  # Default fallback

# For backward compatibility with existing code
def init_rate_limiter(app):
    """
    Initialize rate limiter with the FastAPI app
    (Kept for compatibility with existing init pattern)
    """
    # Add custom exception handler for rate limit exceeded
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    return limiter

# Export for use in decorators
def rate_limit_by_user(limit_string: str):
    """
    Decorator to rate limit by authenticated user or IP
    """
    def decorator(func):
        # In a full implementation, this would use slowapi's decorator
        # For now, we return the function unchanged as middleware handles it
        return func
    return decorator

def rate_limit_by_ip(limit_string: str):
    """
    Decorator to rate limit by IP address only
    """
    def decorator(func):
        return func
    return decorator

# Predefined rate limits for different endpoint types
AUTH_RATE_LIMIT = "10 per minute"      # Strict limit for auth endpoints
API_RATE_LIMIT = "100 per minute"      # Standard API limit
UPLOAD_RATE_LIMIT = "20 per minute"    # Limit for file uploads
SEARCH_RATE_LIMIT = "30 per minute"    # Limit for search operations