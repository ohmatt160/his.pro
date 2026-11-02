"""Short-lived, single-use tickets for cross-origin WebSocket upgrades."""

from __future__ import annotations

import hashlib
import os
import threading
import uuid
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import jwt
import redis
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from app.middleware.jwt import JWT_SECRET_KEY


TICKET_TYPE = "realtime_ticket"
TICKET_AUDIENCE = "hispro-realtime"
_issued_tickets: dict[str, datetime] = {}
_ticket_lock = threading.Lock()


class RealtimeTicketError(ValueError):
    pass


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _ticket_secret() -> str:
    # A dedicated secret is preferable. A derived fallback avoids a new startup
    # dependency while preserving domain separation from access-token signing.
    return os.getenv("REALTIME_TICKET_SECRET") or f"{JWT_SECRET_KEY}:realtime-ticket-v1"


def _ticket_ttl_seconds() -> int:
    try:
        configured = int(os.getenv("REALTIME_TICKET_TTL_SECONDS", "60"))
    except ValueError:
        configured = 60
    return min(max(configured, 15), 120)


def _production_environment() -> bool:
    return (os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "development").lower() in {
        "production",
        "staging",
    }


@lru_cache(maxsize=1)
def _redis_client():
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        return None
    return redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1)


def _ticket_key(jti: str) -> str:
    digest = hashlib.sha256(jti.encode("utf-8")).hexdigest()
    return f"hispro:realtime-ticket:{digest}"


def _record_ticket(jti: str, expires_at: datetime) -> None:
    ttl = max(int((expires_at - _utc_now()).total_seconds()), 1)
    client = _redis_client()
    if client:
        try:
            if not client.set(_ticket_key(jti), "issued", ex=ttl, nx=True):
                raise RealtimeTicketError("Could not issue realtime ticket")
            return
        except redis.RedisError as exc:
            if _production_environment():
                raise RealtimeTicketError("Realtime tickets are temporarily unavailable") from exc

    with _ticket_lock:
        _issued_tickets[jti] = expires_at


def _consume_ticket(jti: str) -> None:
    client = _redis_client()
    if client:
        try:
            consumed = client.getdel(_ticket_key(jti))
            if not consumed:
                raise RealtimeTicketError("Realtime ticket is invalid or already used")
            return
        except AttributeError:
            # Redis 6 compatibility for older hosted services.
            pipeline = client.pipeline(transaction=True)
            pipeline.get(_ticket_key(jti))
            pipeline.delete(_ticket_key(jti))
            existing, _deleted = pipeline.execute()
            if not existing:
                raise RealtimeTicketError("Realtime ticket is invalid or already used")
            return
        except redis.RedisError as exc:
            if _production_environment():
                raise RealtimeTicketError("Realtime tickets are temporarily unavailable") from exc

    with _ticket_lock:
        expires_at = _issued_tickets.pop(jti, None)
    if not expires_at or expires_at <= _utc_now():
        raise RealtimeTicketError("Realtime ticket is invalid or expired")


def issue_realtime_ticket(*, user_id: str, facility_id: str, facility_slug: str, origin: str) -> dict:
    if not all((user_id, facility_id, facility_slug, origin)):
        raise RealtimeTicketError("Realtime ticket context is incomplete")

    now = _utc_now()
    expires_at = now + timedelta(seconds=_ticket_ttl_seconds())
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "tid": str(facility_id),
        "facility_slug": str(facility_slug),
        "origin": origin,
        "jti": jti,
        "type": TICKET_TYPE,
        "aud": TICKET_AUDIENCE,
        "iat": now,
        "exp": expires_at,
    }
    ticket = jwt.encode(payload, _ticket_secret(), algorithm="HS256")
    _record_ticket(jti, expires_at)
    return {"ticket": ticket, "expires_at": expires_at.isoformat()}


def consume_realtime_ticket(ticket: str, *, origin: str | None) -> dict:
    if not ticket or len(ticket) > 4096:
        raise RealtimeTicketError("Realtime ticket is invalid")
    if not origin:
        raise RealtimeTicketError("Realtime origin is required")

    try:
        payload = jwt.decode(
            ticket,
            _ticket_secret(),
            algorithms=["HS256"],
            audience=TICKET_AUDIENCE,
        )
    except ExpiredSignatureError as exc:
        raise RealtimeTicketError("Realtime ticket has expired") from exc
    except InvalidTokenError as exc:
        raise RealtimeTicketError("Realtime ticket is invalid") from exc

    if payload.get("type") != TICKET_TYPE:
        raise RealtimeTicketError("Realtime ticket is invalid")
    if payload.get("origin") != origin:
        raise RealtimeTicketError("Realtime ticket origin does not match")
    if not all(payload.get(field) for field in ("sub", "tid", "facility_slug", "jti")):
        raise RealtimeTicketError("Realtime ticket is invalid")

    _consume_ticket(str(payload["jti"]))
    return payload
