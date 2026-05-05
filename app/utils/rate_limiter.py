"""
Rate limiting utilities for the HIS.Pro API
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import request
import redis
import os

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.getenv('REDIS_URL', 'memory://'),
    strategy="fixed-window"
)

def get_rate_limit_key():
    """
    Generate a rate limit key based on user identity or IP address
    """
    # Try to get user ID from JWT token if authenticated
    try:
        from flask_jwt_extended import get_jwt_identity
        user_id = get_jwt_identity()
        if user_id:
            return f"user:{user_id}"
    except:
        pass
    
    # Fall back to IP address
    return get_remote_address()

def init_rate_limiter(app):
    """
    Initialize rate limiter with the Flask app
    """
    limiter.init_app(app)
    
    # Add custom error handler for rate limit exceeded
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return {
            'error': 'Rate limit exceeded',
            'message': f'You have exceeded the rate limit. Please try again later.',
            'retry_after': e.description
        }, 429
    
    return limiter

# Rate limit decorators for common use cases
def rate_limit_by_user(limit_string):
    """
    Rate limit by authenticated user or IP
    """
    return limiter.limit(limit_string, key_func=get_rate_limit_key)

def rate_limit_by_ip(limit_string):
    """
    Rate limit by IP address only
    """
    return limiter.limit(limit_string, key_func=get_remote_address)

# Predefined rate limits for different endpoint types
AUTH_RATE_LIMIT = "5 per minute"  # Strict limit for auth endpoints
API_RATE_LIMIT = "60 per minute"  # Standard API limit
UPLOAD_RATE_LIMIT = "10 per minute"  # Limit for file uploads
SEARCH_RATE_LIMIT = "30 per minute"  # Limit for search operations
