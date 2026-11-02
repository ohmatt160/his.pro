import asyncio
import os
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.extensions import SessionLocal
from app.middleware.jwt import verify_token
from app.models.facility import Facility
from app.models.user import User
from app.services.realtime_ticket_service import (
    RealtimeTicketError,
    consume_realtime_ticket,
    issue_realtime_ticket,
)
from app.services.realtime_service import (
    REALTIME_KEEPALIVE_TYPE,
    event_visible_to_user,
    public_realtime_event,
    realtime_broker,
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/realtime", tags=["realtime"])
_connections_by_user: dict[str, int] = {}
_connections_by_facility: dict[str, int] = {}


PRODUCTION_ORIGINS = {
    "https://his.pro",
    "https://www.his.pro",
    "https://his-pro.vercel.app",
    "https://his-pro-v1-0.vercel.app",
}
LOCAL_ORIGINS = {
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5175",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:8080",
}


def _allowed_websocket_origins() -> set[str]:
    configured = {
        origin.strip().rstrip("/")
        for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    }
    frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
    if frontend_url:
        configured.add(frontend_url)

    app_env = (os.getenv("APP_ENV") or os.getenv("FLASK_ENV", "development")).lower()
    if app_env == "production":
        return configured or set(PRODUCTION_ORIGINS)
    if app_env == "staging":
        return configured
    return configured | PRODUCTION_ORIGINS | LOCAL_ORIGINS


def _origin_allowed(websocket: WebSocket) -> bool:
    return _origin_value_allowed(websocket.headers.get("origin"))


def _origin_value_allowed(origin: str | None) -> bool:
    app_env = (os.getenv("APP_ENV") or os.getenv("FLASK_ENV", "development")).lower()
    if not origin:
        return app_env not in {"production", "staging"}

    parsed = urlparse(origin)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        return False

    normalized = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    return normalized in _allowed_websocket_origins()


def _connection_limit(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _try_register_connection(user: User) -> bool:
    user_id = str(user.id)
    facility_slug = str(user.facility_slug)
    max_per_user = _connection_limit("REALTIME_MAX_CONNECTIONS_PER_USER", 5)
    max_per_facility = _connection_limit("REALTIME_MAX_CONNECTIONS_PER_FACILITY", 1000)

    if _connections_by_user.get(user_id, 0) >= max_per_user:
        return False
    if _connections_by_facility.get(facility_slug, 0) >= max_per_facility:
        return False

    _connections_by_user[user_id] = _connections_by_user.get(user_id, 0) + 1
    _connections_by_facility[facility_slug] = _connections_by_facility.get(facility_slug, 0) + 1
    return True


def _unregister_connection(user: User) -> None:
    user_id = str(user.id)
    facility_slug = str(user.facility_slug)
    for registry, key in ((_connections_by_user, user_id), (_connections_by_facility, facility_slug)):
        current = registry.get(key, 0)
        if current <= 1:
            registry.pop(key, None)
        else:
            registry[key] = current - 1


def _token_from_websocket(websocket: WebSocket) -> str | None:
    cookie_token = websocket.cookies.get("hispro_access_token")
    if cookie_token:
        return cookie_token

    authorization = websocket.headers.get("authorization") or websocket.headers.get("x-hispro-authorization")
    if authorization:
        try:
            scheme, token = authorization.split()
            if scheme.lower() == "bearer":
                return token
        except ValueError:
            return None
    return None


def _authenticate_websocket_user(websocket: WebSocket) -> User | None:
    db: Session = SessionLocal()
    try:
        ticket = websocket.query_params.get("ticket")
        if ticket:
            try:
                payload = consume_realtime_ticket(
                    ticket,
                    origin=websocket.headers.get("origin"),
                )
            except RealtimeTicketError:
                return None
        else:
            token = _token_from_websocket(websocket)
            if not token:
                return None
            payload = verify_token(token)

        user = db.query(User).filter(User.id == payload.get("sub"), User.is_active == True).first()
        if not user or not user.facility_slug:
            return None
        tenant_id = payload.get("tid") or user.facility_id
        facility = (
            db.query(Facility)
            .filter(
                Facility.id == tenant_id,
                Facility.slug == user.facility_slug,
                Facility.is_active == True,
            )
            .first()
        )
        if not facility:
            return None
        if ticket and (
            str(user.facility_id) != str(payload.get("tid"))
            or user.facility_slug != payload.get("facility_slug")
        ):
            return None
        db.expunge(user)
        return user
    finally:
        db.close()


@router.post("/ticket")
async def create_realtime_ticket(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    origin = request.headers.get("origin")
    if not _origin_value_allowed(origin):
        raise HTTPException(status_code=403, detail="Realtime origin is not allowed")
    if not current_user.facility_id or not current_user.facility_slug:
        raise HTTPException(status_code=403, detail="Realtime is unavailable for this account")
    try:
        return issue_realtime_ticket(
            user_id=str(current_user.id),
            facility_id=str(current_user.facility_id),
            facility_slug=current_user.facility_slug,
            origin=origin or "",
        )
    except RealtimeTicketError as exc:
        raise HTTPException(status_code=503, detail="Realtime is temporarily unavailable") from exc


@router.websocket("/ws")
async def realtime_websocket(websocket: WebSocket):
    if not _origin_allowed(websocket):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user = _authenticate_websocket_user(websocket)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if not _try_register_connection(user):
        await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER)
        return

    await websocket.accept()
    facility_slug = user.facility_slug
    queue = await realtime_broker.subscribe(facility_slug)

    async def keepalive() -> None:
        while True:
            await asyncio.sleep(25)
            await websocket.send_json({"type": REALTIME_KEEPALIVE_TYPE})

    keepalive_task = asyncio.create_task(keepalive())
    try:
        await websocket.send_json({"type": "system.connected", "facility_slug": facility_slug})
        while True:
            event = await queue.get()
            if event_visible_to_user(event, user):
                await websocket.send_json(public_realtime_event(event))
    except WebSocketDisconnect:
        pass
    finally:
        keepalive_task.cancel()
        _unregister_connection(user)
        await realtime_broker.unsubscribe(facility_slug, queue)
