"""
Authentication Routes - FastAPI Version
Converted from Flask-RESTx auth_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
import logging

from app.services.auth_service import AuthService
from app.utils.validators import Validators
from app.middleware.jwt import verify_token
from app.models.user import User
from app.extensions import get_db

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["authentication"])

# Security scheme
security = HTTPBearer()


# Pydantic models for request/response
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = Field(..., pattern="^(admin|doctor|nurse|staff|patient)$")
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    facility_slug: Optional[str] = Field(None, max_length=100)


class UserLogin(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    first_name: Optional[str]
    last_name: Optional[str]
    facility_slug: Optional[str]
    is_active: bool
    created_at: str
    updated_at: Optional[str]


class MessageResponse(BaseModel):
    message: str


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegister,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Register a new user
    """
    try:
        # Sanitize input fields
        data = user_data.dict()
        data['username'] = Validators.sanitize_string(data.get('username', ''))
        data['email'] = Validators.sanitize_string(data.get('email', ''))
        if data.get('first_name'):
            data['first_name'] = Validators.sanitize_string(data['first_name'])
        if data.get('last_name'):
            data['last_name'] = Validators.sanitize_string(data['last_name'])
        
        logger.info(f"[Register] Creating user with data: {data}")
        
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
            facility_slug=user.facility_slug,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else "",
            updated_at=user.updated_at.isoformat() if user.updated_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Register] Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/login", response_model=TokenResponse)
async def login_user(
    login_data: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Login and get access token
    """
    try:
        # Sanitize input
        data = login_data.dict()
        data['username'] = Validators.sanitize_string(data.get('username', ''))
        
        # Authenticate user
        user, error = AuthService.authenticate_user(data['username'], data['password'], db)
        
        if error:
            logger.warning(f"[Login] Authentication failed for user: {data['username']}")
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Validate facility access if requested
        requested_facility = request.query_params.get('facility_slug')
        if requested_facility and user.facility_slug != requested_facility:
            logger.warning(f"[Login] User {user.username} tried to access wrong facility")
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Create tokens
        from app.middleware.jwt import create_access_token, create_refresh_token
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        # Prepare user response
        user_data = UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            first_name=user.first_name,
            last_name=user.last_name,
            facility_slug=user.facility_slug,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else "",
            updated_at=user.updated_at.isoformat() if user.updated_at else None
        )
        
        logger.info(f"[Login] User {user.username} logged in successfully")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Login] Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    try:
        # Verify the refresh token
        token_data = verify_token(credentials.credentials, token_type="refresh")
        user_id = token_data.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        # Verify user exists and is active
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        
        # Create new access token
        from app.middleware.jwt import create_access_token
        new_access_token = create_access_token(identity=user.id)
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=credentials.credentials  # Return same refresh token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Refresh] Exception: {str(e)}")
        raise HTTPException(status_code=401, detail="Could not refresh token")


@router.post("/logout", response_model=MessageResponse)
async def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Logout user by adding token to blocklist
    """
    try:
        # Verify the access token
        token_data = verify_token(credentials.credentials, token_type="access")
        jti = token_data.get("jti")
        user_id = token_data.get("sub")
        
        if not jti:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Add token to blocklist (Redis or in-memory)
        from app import jwt_blocklist
        jwt_blocklist.add(jti)
        
        return MessageResponse(message="Logout successful")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Logout] Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")