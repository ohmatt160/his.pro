"""
User Profile Routes - FastAPI Version
Converted from Flask-RESTx user_profile_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
import logging

from app.extensions import get_db
from app.services.user_profile_service import UserProfileService
from app.utils.validators import Validators
from app.utils.dependencies import get_current_user, role_required
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = Field(None)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    facility_slug: Optional[str]
    is_active: bool
    created_at: str
    updated_at: Optional[str]


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)


class MessageResponse(BaseModel):
    message: str


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user's profile"""
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        phone=current_user.phone,
        facility_slug=current_user.facility_slug,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat() if current_user.created_at else "",
        updated_at=current_user.updated_at.isoformat() if current_user.updated_at else None
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile"""
    # Sanitize fields
    payload = data.dict(exclude_unset=True)
    for key, value in payload.items():
        if isinstance(value, str):
            payload[key] = Validators.sanitize_string(value)

    updated_user = UserProfileService.update_profile(current_user, payload)

    return UserResponse(
        id=str(updated_user.id),
        username=updated_user.username,
        email=updated_user.email,
        role=updated_user.role,
        first_name=updated_user.first_name,
        last_name=updated_user.last_name,
        phone=updated_user.phone,
        facility_slug=updated_user.facility_slug,
        is_active=updated_user.is_active,
        created_at=updated_user.created_at.isoformat() if updated_user.created_at else "",
        updated_at=updated_user.updated_at.isoformat() if updated_user.updated_at else None
    )


@router.post("/me/change-password", response_model=MessageResponse)
async def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change current user's password"""
    from app.services.auth_service import AuthService

    success, message = AuthService.change_password(current_user.id, data.current_password, data.new_password)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    return MessageResponse(message=message)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Get user by ID (admin only)"""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        role=user.role,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        facility_slug=user.facility_slug,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
        updated_at=user.updated_at.isoformat() if user.updated_at else None
    )


@router.put("/{user_id}/activate", response_model=MessageResponse)
async def toggle_user_activation(
    user_id: str,
    activate: bool = True,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Activate or deactivate a user (admin only)"""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = activate
    user.save()

    action = "activated" if activate else "deactivated"
    return MessageResponse(message=f"User {action} successfully")
