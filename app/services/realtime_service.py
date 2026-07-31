import asyncio
import json
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any
from app.services.metrics_service import metrics_service

try:
    import redis.asyncio as redis_async
except Exception:  # pragma: no cover - redis is optional in local installs
    redis_async = None


REALTIME_KEEPALIVE_TYPE = "system.keepalive"
REALTIME_REDIS_CHANNEL = "hispro:realtime-events"
logger = logging.getLogger(__name__)


def _user_branch_ids(user) -> set[str]:
    branch_ids = {
        str(value)
        for value in (
            getattr(user, "branch_id", None),
            getattr(user, "department_id", None),
        )
        if value
    }
    for collection_name in ("branch_ids", "departments"):
        for value in getattr(user, collection_name, None) or []:
            if value:
                branch_ids.add(str(value))
    return branch_ids


def build_realtime_event(
    *,
    event_type: str,
    facility_slug: str,
    branch_id: str | None = None,
    user_id: str | None = None,
    roles: list[str] | tuple[str, ...] | None = None,
    modules: list[str] | tuple[str, ...] | None = None,
    resource_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "type": event_type,
        "facility_slug": facility_slug,
        "branch_id": str(branch_id) if branch_id else None,
        "user_id": str(user_id) if user_id else None,
        "roles": [role.upper() for role in roles or []],
        "modules": list(modules or []),
        "resource_id": str(resource_id) if resource_id else None,
        "payload": payload or {},
        "occurred_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def event_visible_to_user(event: dict[str, Any], user) -> bool:
    if not user or event.get("facility_slug") != getattr(user, "facility_slug", None):
        return False

    event_user_id = event.get("user_id")
    if event_user_id and str(event_user_id) != str(getattr(user, "id", "")):
        return False

    user_role = (getattr(user, "role", "") or "").upper()
    roles = set(event.get("roles") or [])
    if roles and user_role not in roles:
        return False

    branch_id = event.get("branch_id")
    if branch_id and user_role != "ADMIN" and str(branch_id) not in _user_branch_ids(user):
        return False

    return True


def public_realtime_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in event.items()
        if key not in {"roles", "user_id"}
    }


class RealtimeBroker:
    def __init__(self, queue_size: int = 100):
        self.queue_size = queue_size
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}
        self._redis = None
        self._listener_task: asyncio.Task | None = None
        self._redis_failed = False
        self._started = False

    async def start(self) -> None:
        """Enable external fanout after the application lifespan has started."""
        self._started = True

    async def subscribe(self, facility_slug: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self.queue_size)
        self._subscribers.setdefault(facility_slug, set()).add(queue)
        metrics_service.increment("realtime_subscriptions_total")
        metrics_service.set_gauge("realtime_connections", self.connection_count())
        await self._ensure_redis_listener()
        return queue

    async def unsubscribe(self, facility_slug: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        subscribers = self._subscribers.get(facility_slug)
        if not subscribers:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._subscribers.pop(facility_slug, None)
        metrics_service.set_gauge("realtime_connections", self.connection_count())

    async def _publish_local(self, event: dict[str, Any]) -> None:
        facility_slug = event.get("facility_slug")
        if not facility_slug:
            return

        for queue in list(self._subscribers.get(facility_slug, set())):
            if queue.full():
                try:
                    queue.get_nowait()
                    metrics_service.increment("realtime_dropped_events_total")
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                metrics_service.increment("realtime_dropped_events_total")
                pass

    async def _ensure_redis_listener(self) -> None:
        if not self._started or self._listener_task or self._redis_failed:
            return
        redis_url = os.getenv("REDIS_URL")
        if not redis_url or redis_async is None:
            return
        try:
            self._redis = redis_async.from_url(redis_url, socket_connect_timeout=5)
            await self._redis.ping()
        except Exception:
            self._redis_failed = True
            self._redis = None
            metrics_service.increment("realtime_redis_failures_total")
            logger.warning("Realtime Redis unavailable; falling back to in-memory events", exc_info=True)
            return
        self._listener_task = asyncio.create_task(self._redis_listener())

    async def _redis_listener(self) -> None:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(REALTIME_REDIS_CHANNEL)
        try:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                try:
                    raw = message.get("data")
                    event = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
                    await self._publish_local(event)
                except Exception:
                    metrics_service.increment("realtime_malformed_events_total")
                    logger.warning("Dropped malformed realtime Redis event", exc_info=True)
        finally:
            await pubsub.unsubscribe(REALTIME_REDIS_CHANNEL)
            await pubsub.aclose()

    async def publish(self, event: dict[str, Any]) -> None:
        await self._ensure_redis_listener()
        if self._redis is not None:
            try:
                await self._redis.publish(REALTIME_REDIS_CHANNEL, json.dumps(event, default=str))
                return
            except Exception:
                metrics_service.increment("realtime_redis_failures_total")
                logger.warning("Realtime Redis publish failed; using local fallback", exc_info=True)
        await self._publish_local(event)

    async def close(self) -> None:
        self._started = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

        if self._redis is not None:
            try:
                await self._redis.aclose()
            except Exception:
                logger.warning("Realtime Redis close failed", exc_info=True)
            self._redis = None

        self._subscribers.clear()
        self._redis_failed = False
        metrics_service.set_gauge("realtime_connections", 0)

    def connection_count(self) -> int:
        return sum(len(subscribers) for subscribers in self._subscribers.values())

    def stats(self) -> dict[str, Any]:
        return {
            "connections": self.connection_count(),
            "facilities": len(self._subscribers),
            "redis_configured": bool(os.getenv("REDIS_URL")),
            "redis_failed": self._redis_failed,
            "started": self._started,
        }


realtime_broker = RealtimeBroker()


def publish_tenant_event(**kwargs: Any) -> None:
    event = build_realtime_event(**kwargs)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(realtime_broker.publish(event))
