"""
Authentication Routes - FastAPI Version
Converted from Flask-RESTx auth_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import or_
from sqlalchemy.orm import Session
import logging
import os
import uuid

from app.schemas.users import (
    MessageResponse,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    UserSessionResponse,
)
from app.services.auth_service import AuthService
from app.services.session_service import SessionService
from app.utils.validators import Validators
from app.middleware.jwt import JWT_ACCESS_TOKEN_EXPIRES, JWT_REFRESH_TOKEN_EXPIRES, verify_token
from app.models.user import User
from app.models.branch import Branch
from app.models.user_session import UserSession
from app.extensions import get_db

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["authentication"])

# Security scheme
security = HTTPBearer(auto_error=False)


def _cookie_secure() -> bool:
    return os.getenv("APP_ENV") == "production" or os.getenv("COOKIE_SECURE", "").lower() == "true"


def _set_auth_cookies(response: Response, token_response: TokenResponse) -> None:
    secure = _cookie_secure()
    same_site = "none" if secure else "lax"
    response.set_cookie(
        "hispro_access_token",
        token_response.access_token,
        max_age=JWT_ACCESS_TOKEN_EXPIRES,
        httponly=True,
        secure=secure,
        samesite=same_site,
        path="/",
    )
    response.set_cookie(
        "hispro_refresh_token",
        token_response.refresh_token,
        max_age=JWT_REFRESH_TOKEN_EXPIRES,
        httponly=True,
        secure=secure,
        samesite=same_site,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    secure = _cookie_secure()
    same_site = "none" if secure else "lax"
    for cookie_name in ("hispro_access_token", "hispro_refresh_token"):
        response.delete_cookie(cookie_name, path="/", secure=secure, samesite=same_site)


def _get_token_from_request(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
    cookie_name: str,
) -> str | None:
    if credentials and credentials.credentials:
        return credentials.credentials
    return request.cookies.get(cookie_name)



def _user_branch_values(user: User) -> set[str]:
    values = {str(value) for value in (user.branch_ids or []) if value}
    values.update(str(value) for value in (user.departments or []) if value)
    if user.branch_id:
        values.add(str(user.branch_id))
    if user.department_id:
        values.add(str(user.department_id))
    return values


def _user_has_branch_assignment(user: User) -> bool:
    return bool(_user_branch_values(user))


def _validate_requested_branch(user: User, facility_slug: str | None, branch_slug: str | None, db: Session) -> None:
    role = (user.role or "").upper()
    if not branch_slug:
        if role != "ADMIN" and _user_has_branch_assignment(user):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return

    if not facility_slug:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    branch = (
        db.query(Branch)
        .filter_by(facility_slug=facility_slug, slug=branch_slug, is_active=True)
        .first()
    )
    if not branch:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    allowed = _user_branch_values(user)
    if str(branch.id) not in allowed and str(branch.slug) not in allowed:
        raise HTTPException(status_code=401, detail="Invalid credentials")


def _user_branch_slugs(user: User, db: Session) -> list[str]:
    branch_values = _user_branch_values(user)
    if not branch_values:
        return []

    branches = (
        db.query(Branch)
        .filter(
            Branch.is_active == True,
            or_(Branch.id.in_(branch_values), Branch.slug.in_(branch_values)),
        )
        .all()
    )
    return [branch.slug for branch in branches if branch.slug]

def build_token_response(user: User, request: Request | None = None) -> TokenResponse:
    from app.middleware.jwt import create_access_token, create_refresh_token

    refresh_jti = str(uuid.uuid4())
    session = SessionService.create_session(str(user.id), refresh_jti, request)
    return TokenResponse(
        access_token=create_access_token(identity=user.id, session_id=session.id, tenant_id=user.facility_id),
        refresh_token=create_refresh_token(identity=user.id, session_id=session.id, jti=refresh_jti, tenant_id=user.facility_id),
    )


def sanitize_registration_data(user_data: UserRegister) -> dict:
    data = user_data.model_dump()
    data['username'] = Validators.sanitize_string(data.get('username', ''))
    data['email'] = Validators.sanitize_string(data.get('email', ''))
    if data.get('first_name'):
        data['first_name'] = Validators.sanitize_string(data['first_name'])
    if data.get('last_name'):
        data['last_name'] = Validators.sanitize_string(data['last_name'])
    return data

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegister,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Register a new user
    """
    try:
        # Sanitize input fields
        data = sanitize_registration_data(user_data)
        
        logger.info("[Register] Creating user %s", data.get("username"))
        
        # Create user
        user, error = AuthService.register_user(data, db)
        
        if error:
            logger.warning(f"[Register] Error: {error}")
            raise HTTPException(status_code=400, detail=error)
        
        logger.info(f"[Register] User created successfully: {user.username}")
        
        # Return user data (excluding sensitive fields)
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            first_name=user.first_name,
            last_name=user.last_name,
            facility_id=str(user.facility_id) if user.facility_id else None,
            facility_slug=user.facility_slug,
            branch_id=user.branch_id or user.department_id,
            branch_ids=user.branch_ids or user.departments or [],
            branch_slug=(_user_branch_slugs(user, db) or [None])[0],
            branch_slugs=_user_branch_slugs(user, db),
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else "",
            updated_at=user.updated_at.isoformat() if user.updated_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[Register] Exception: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post("/ensure", response_model=TokenResponse)
async def ensure_user(
    user_data: UserRegister,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Create a setup user if it does not exist, or authenticate the existing user.
    """
    try:
        data = sanitize_registration_data(user_data)
        existing_user = db.query(User).filter_by(username=data['username']).first()

        if existing_user:
            if not existing_user.is_active or not existing_user.check_password(data['password']):
                raise HTTPException(status_code=401, detail="Invalid credentials")

            if existing_user.email != data['email']:
                raise HTTPException(status_code=409, detail="Username already belongs to another email")

            logger.info(f"[Ensure] Existing user authenticated: {existing_user.username}")
            token_response = build_token_response(existing_user, request)
            _set_auth_cookies(response, token_response)
            return token_response

        user, error = AuthService.register_user(data, db)

        if error:
            logger.warning(f"[Ensure] Error: {error}")
            raise HTTPException(status_code=400, detail=error)

        logger.info(f"[Ensure] User created and authenticated: {user.username}")
        token_response = build_token_response(user, request)
        _set_auth_cookies(response, token_response)
        return token_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[Ensure] Exception: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Setup authentication failed")


@router.post("/login", response_model=TokenResponse)
async def login_user(
    login_data: UserLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Login and get access token
    """
    try:
        # Sanitize input
        data = login_data.model_dump()
        data['username'] = Validators.sanitize_string(data.get('username', ''))
        
        # Authenticate user
        user, error = AuthService.authenticate_user(data['username'], data['password'], db)
        
        if error:
            logger.warning(f"[Login] Authentication failed for user: {data['username']}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Validate facility access if requested
        requested_facility = request.query_params.get('facility_slug')
        requested_branch = request.query_params.get('branch_slug')
        if requested_facility and user.facility_slug != requested_facility:
            logger.warning(f"[Login] User {user.username} tried to access wrong facility")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        _validate_requested_branch(user, requested_facility or user.facility_slug, requested_branch, db)
        
        logger.info(f"[Login] User {user.username} logged in successfully")
        
        token_response = build_token_response(user, request)
        _set_auth_cookies(response, token_response)
        return token_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[Login] Exception: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    try:
        refresh_token_value = _get_token_from_request(request, credentials, "hispro_refresh_token")
        if not refresh_token_value:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        token_data = verify_token(refresh_token_value, token_type="refresh")
        user_id = token_data.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        # Verify user exists and is active
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        from app.middleware.jwt import create_access_token, create_refresh_token
        new_refresh_jti = str(uuid.uuid4())
        SessionService.rotate_refresh_token(token_data.get("sid"), user_id, new_refresh_jti)
        token_response = TokenResponse(
            access_token=create_access_token(identity=user.id, session_id=token_data.get("sid"), tenant_id=user.facility_id),
            refresh_token=create_refresh_token(identity=user.id, session_id=token_data.get("sid"), jti=new_refresh_jti, tenant_id=user.facility_id),
        )
        _set_auth_cookies(response, token_response)
        
        return token_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Refresh] Exception: {str(e)}")
        raise HTTPException(status_code=401, detail="Could not refresh token")


@router.post("/logout", response_model=MessageResponse)
async def logout_user(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Logout user by adding token to blocklist
    """
    try:
        access_token_value = _get_token_from_request(request, credentials, "hispro_access_token")
        if not access_token_value:
            raise HTTPException(status_code=401, detail="Invalid token")

        token_data = verify_token(access_token_value, token_type="access")
        jti = token_data.get("jti")
        user_id = token_data.get("sub")
        
        if not jti:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Add token to blocklist (Redis or in-memory)
        from app import jwt_blocklist
        jwt_blocklist.add(jti)
        SessionService.revoke_session_by_id(token_data.get("sid"), user_id)
        _clear_auth_cookies(response)
        
        return MessageResponse(message="Logout successful")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[Logout] Exception: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Logout failed")


@router.post("/logout-everywhere", response_model=MessageResponse)
async def logout_everywhere(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    access_token_value = _get_token_from_request(request, credentials, "hispro_access_token")
    if not access_token_value:
        raise HTTPException(status_code=401, detail="Invalid token")

    token_data = verify_token(access_token_value, token_type="access")
    revoked = SessionService.revoke_all_for_user(token_data.get("sub"))
    _clear_auth_cookies(response)
    return MessageResponse(message=f"Logged out {revoked} active session(s)")


@router.get("/sessions", response_model=list[UserSessionResponse])
async def list_sessions(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
):
    access_token_value = _get_token_from_request(request, credentials, "hispro_access_token")
    if not access_token_value:
        raise HTTPException(status_code=401, detail="Invalid token")

    token_data = verify_token(access_token_value, token_type="access")
    user_id = token_data.get("sub")
    current_session_id = token_data.get("sid")
    sessions = (
        db.query(UserSession)
        .filter_by(user_id=str(user_id), is_active=True)
        .order_by(UserSession.last_seen_at.desc())
        .all()
    )

    return [
        UserSessionResponse(
            id=str(session.id),
            user_agent=session.user_agent,
            ip_address=session.ip_address,
            last_seen_at=session.last_seen_at.isoformat() if session.last_seen_at else "",
            expires_at=session.expires_at.isoformat() if session.expires_at else "",
            is_current=str(session.id) == str(current_session_id),
        )
        for session in sessions
        if session.revoked_at is None
    ]


@router.post("/verify", response_model=UserResponse)
async def verify_current_session(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
):
    access_token_value = _get_token_from_request(request, credentials, "hispro_access_token")
    if not access_token_value:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    token_data = verify_token(access_token_value, token_type="access")
    user = db.query(User).filter(User.id == token_data.get("sub"), User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        first_name=user.first_name,
        last_name=user.last_name,
        facility_id=str(user.facility_id) if user.facility_id else None,
        facility_slug=user.facility_slug,
        branch_id=user.branch_id or user.department_id,
        branch_ids=user.branch_ids or user.departments or [],
        branch_slug=(_user_branch_slugs(user, db) or [None])[0],
        branch_slugs=_user_branch_slugs(user, db),
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )
