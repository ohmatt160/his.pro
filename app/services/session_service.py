from datetime import UTC, datetime, timedelta
import uuid

from fastapi import HTTPException, Request, status

from app.extensions import db_session
from app.models.user_session import UserSession

SESSION_INACTIVITY_TIMEOUT_SECONDS = 30 * 60
REFRESH_SESSION_DAYS = 7


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class SessionService:
    """Manage database-backed user sessions."""

    @staticmethod
    def create_session(user_id: str, refresh_jti: str, request: Request | None = None) -> UserSession:
        session = UserSession(
            id=str(uuid.uuid4()),
            user_id=str(user_id),
            refresh_jti=refresh_jti,
            user_agent=(request.headers.get("user-agent")[:255] if request else None),
            ip_address=SessionService._client_ip(request) if request else None,
            expires_at=utc_now() + timedelta(days=REFRESH_SESSION_DAYS),
            last_seen_at=utc_now(),
            is_active=True,
        )
        db_session.add(session)
        db_session.flush()
        return session

    @staticmethod
    def validate_session(
        session_id: str | None,
        user_id: str | None,
        token_type: str,
        refresh_jti: str | None = None,
        touch: bool = True,
    ) -> UserSession | None:
        if not session_id:
            return None

        session = db_session.query(UserSession).filter_by(id=session_id, user_id=str(user_id)).first()
        if (
            not session
            or not session.is_active
            or session.revoked_at is not None
            or session.expires_at <= utc_now()
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has expired")

        if token_type == "access":
            inactive_for = utc_now() - session.last_seen_at
            if inactive_for.total_seconds() > SESSION_INACTIVITY_TIMEOUT_SECONDS:
                SessionService.revoke_session(session)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has expired")
            if touch:
                session.last_seen_at = utc_now()
                db_session.add(session)
                db_session.flush()

        if token_type == "refresh" and refresh_jti and session.refresh_jti != refresh_jti:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has expired")

        return session

    @staticmethod
    def rotate_refresh_token(session_id: str, user_id: str, refresh_jti: str) -> None:
        session = SessionService.validate_session(
            session_id,
            user_id,
            token_type="refresh",
            touch=False,
        )
        session.refresh_jti = refresh_jti
        session.last_seen_at = utc_now()
        db_session.add(session)
        db_session.flush()

    @staticmethod
    def revoke_session(session: UserSession) -> None:
        session.is_active = False
        session.revoked_at = utc_now()
        db_session.add(session)
        db_session.flush()

    @staticmethod
    def revoke_session_by_id(session_id: str | None, user_id: str | None = None) -> None:
        if not session_id:
            return

        query = db_session.query(UserSession).filter_by(id=session_id)
        if user_id:
            query = query.filter_by(user_id=str(user_id))
        session = query.first()
        if session:
            SessionService.revoke_session(session)

    @staticmethod
    def revoke_all_for_user(user_id: str) -> int:
        sessions = (
            db_session.query(UserSession)
            .filter_by(user_id=str(user_id), is_active=True)
            .all()
        )
        for session in sessions:
            SessionService.revoke_session(session)
        return len(sessions)

    @staticmethod
    def _client_ip(request: Request | None) -> str | None:
        if not request:
            return None
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else None
