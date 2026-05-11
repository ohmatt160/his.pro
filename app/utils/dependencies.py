"""
FastAPI Dependencies for Authentication and Authorization
Converted from Flask decorators to FastAPI Depends pattern
"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List
import logging

from app.extensions import get_db, engine
from app.models.user import User
from app.middleware.jwt import verify_token
from app import jwt_blocklist

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    try:
        # Verify token
        token_data = verify_token(credentials.credentials)
        user_id = int(token_data.get("sub"))

        # Get user from database
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        # Attach user to request state for middleware
        request.state.user_id = user.id
        request.state.user = token_data

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
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            logger.warning(f"User {user.username} with role {user.role} attempted to access restricted endpoint. Required roles: {roles}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden. Insufficient permissions."
            )
        return user
    return dependency


async def verify_refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Verify a refresh token and return its payload

    Returns:
        dict: Token payload with user identity

    Raises:
        HTTPException: 401 if token is invalid
    """
    try:
        token_data = verify_token(credentials.credentials, token_type="refresh")
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
    if not authorization:
        return None

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None

        token_data = verify_token(token)
        user_id = int(token_data.get("sub"))
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        return user
    except Exception:
        return None
