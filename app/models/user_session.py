from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models.base_model import BaseModel


class UserSession(BaseModel):
    """Database-backed login session for refresh rotation and logout-everywhere."""

    __tablename__ = "user_sessions"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    refresh_jti = Column(String(64), nullable=False, unique=True, index=True)
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(64), nullable=True)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    user = relationship("User", backref="sessions")
