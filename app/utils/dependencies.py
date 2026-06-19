"""
FastAPI Dependencies for Authentication and Authorization
Converted from Flask decorators to FastAPI Depends pattern
"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List
import logging
from datetime import datetime

from app.extensions import get_db, engine
from app.models.user import User
from app.middleware.jwt import verify_token
from app.models.facility import Facility
from app import jwt_blocklist

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)


def _token_from_request(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
    cookie_name: str,
) -> str | None:
    if credentials and credentials.credentials:
        return credentials.credentials
    return request.cookies.get(cookie_name)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    try:
        token = _token_from_request(request, credentials, "hispro_access_token")
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )

        token_data = verify_token(token)
        user_id = token_data.get("sub")

        # Get user from database
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        if user.facility_slug and not user.facility_id:
            facility = db.query(Facility).filter_by(slug=user.facility_slug, is_active=True).first()
            if facility:
                user.facility_id = facility.id
                db.add(user)
                db.flush()

        # Attach user to request state for middleware
        user.last_active = datetime.utcnow()
        db.add(user)
        db.flush()
        request.state.user_id = user.id
        request.state.user = token_data
        request.state.tenant_id = str(user.facility_id) if user.facility_id else token_data.get("tid")

        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


def role_required(*roles: List[str]):
    """
    Dependency to require specific roles for endpoint access

    Args:
        *roles: List of allowed roles (e.g., 'ADMIN', 'DOCTOR')

    Returns:
        FastAPI dependency function
    """
    async def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            logger.warning(f"User {user.username} with role {user.role} attempted to access restricted endpoint. Required roles: {roles}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden. Insufficient permissions."
            )
        return user
    return dependency


async def verify_refresh_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security)
) -> dict:
    """
    Verify a refresh token and return its payload

    Returns:
        dict: Token payload with user identity

    Raises:
        HTTPException: 401 if token is invalid
    """
    try:
        token = _token_from_request(request, credentials, "hispro_refresh_token")
        if not token:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        token_data = verify_token(token, token_type="refresh")
        return token_data
    except HTTPException:
        raise


# For public endpoints that don't require authentication
def optional_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User | None:
    """
    Optional authentication - returns user if token is valid, otherwise None
    """
    authorization = request.headers.get("Authorization")
    cookie_token = request.cookies.get("hispro_access_token")
    if not authorization and not cookie_token:
        return None

    try:
        if authorization:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                return None
        else:
            token = cookie_token

        token_data = verify_token(token)
        user_id = token_data.get("sub")
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        return user
    except Exception:
        return None
