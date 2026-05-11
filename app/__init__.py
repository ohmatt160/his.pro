"""
Shared application components - JWT blocklist and common utilities
This module provides shared resources for the FastAPI application.
"""

import os
import redis

# JWT token blocklist (supports both in-memory and Redis)
USE_REDIS = os.getenv('REDIS_URL', '') != ''

if USE_REDIS:
    # Production: Use Redis for distributed blocklist
    redis_client = redis.from_url(os.getenv('REDIS_URL'))

    class JWTBlocklist:
        """Redis-based JWT blocklist for production"""

        @staticmethod
        def add(jti: str):
            """Add token to blocklist"""
            redis_client.setex(f"jwt_blocklist:{jti}", 86400, "1")  # 24hr TTL

        @staticmethod
        def is_blocklisted(jti: str) -> bool:
            """Check if token is blocklisted"""
            return redis_client.exists(f"jwt_blocklist:{jti}") > 0

    jwt_blocklist = JWTBlocklist()
else:
    # Development: Use in-memory set
    jwt_blocklist_set = set()

    class JWTBlocklist:
        """In-memory JWT blocklist for development"""

        @staticmethod
        def add(jti: str):
            """Add token to blocklist"""
            jwt_blocklist_set.add(jti)

        @staticmethod
        def is_blocklisted(jti: str) -> bool:
            """Check if token is blocklisted"""
            return jti in jwt_blocklist_set

    jwt_blocklist = JWTBlocklist()
