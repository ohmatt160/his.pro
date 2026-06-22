import json
import logging
import os
from typing import Any

import redis


logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL")


def _client():
    if not REDIS_URL:
        return None
    try:
        return redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
    except Exception:
        logger.exception("Redis cache client could not be initialized")
        return None


redis_client = _client()


def cache_get(key: str):
    if not redis_client:
        return None
    try:
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except Exception:
        logger.exception("Cache get failed for key %s", key)
        return None


def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    if not redis_client:
        return
    try:
        redis_client.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        logger.exception("Cache set failed for key %s", key)


def cache_delete(pattern: str) -> None:
    if not redis_client:
        return
    try:
        for key in redis_client.scan_iter(pattern):
            redis_client.delete(key)
    except Exception:
        logger.exception("Cache delete failed for pattern %s", pattern)
