"""
User Profile Routes - FastAPI Version
Converted from Flask-RESTx user_profile_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
import logging

from app.extensions import get_db
from app.schemas.password_reset import ChangePasswordRequest
from app.schemas.users import UserResponse, UserUpdate, MessageResponse
from app.services.user_profile_service import UserProfileService
from app.utils.validators import Validators
from app.utils.dependencies import get_current_user, role_required
from app.models.user import User
from app.services.audit_log_service import AuditLogService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])




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
        facility_id=str(current_user.facility_id) if current_user.facility_id else None,
        facility_slug=current_user.facility_slug,
        branch_id=current_user.branch_id or current_user.department_id,
        branch_ids=current_user.branch_ids or current_user.departments or [],
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat() if current_user.created_at else "",
        updated_at=current_user.updated_at.isoformat() if current_user.updated_at else None
    )



@router.put("/me", response_model=UserResponse)
async def update_current_user(
    data: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile"""
    # Sanitize fields
    payload = data.model_dump(exclude_unset=True)
    for key, value in payload.items():
        if isinstance(value, str):
            payload[key] = Validators.sanitize_string(value)

    updated_user, error = UserProfileService.update_profile(current_user, payload)
    if error:
        raise HTTPException(status_code=409, detail=error)

    AuditLogService.log_action(
        user_id=current_user.id,
        action="UPDATE_PROFILE",
        resource_type="user",
        resource_id=current_user.id,
        facility_slug=current_user.facility_slug,
        details={"fields": sorted(payload.keys())},
        request=request,
    )

    return UserResponse(
        id=str(updated_user.id),
        username=updated_user.username,
        email=updated_user.email,
        role=updated_user.role,
        first_name=updated_user.first_name,
        last_name=updated_user.last_name,
        phone=updated_user.phone,
        facility_id=str(updated_user.facility_id) if updated_user.facility_id else None,
        facility_slug=updated_user.facility_slug,
        branch_id=updated_user.branch_id or updated_user.department_id,
        branch_ids=updated_user.branch_ids or updated_user.departments or [],
        is_active=updated_user.is_active,
        created_at=updated_user.created_at.isoformat() if updated_user.created_at else "",
        updated_at=updated_user.updated_at.isoformat() if updated_user.updated_at else None
    )


@router.post("/me/change-password", response_model=MessageResponse)
async def change_password(
    data: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change current user's password"""
    from app.services.auth_service import AuthService

    success, message = AuthService.change_password(current_user.id, data.current_password, data.new_password)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    AuditLogService.log_action(
        user_id=current_user.id,
        action="CHANGE_PASSWORD",
        resource_type="user",
        resource_id=current_user.id,
        facility_slug=current_user.facility_slug,
        details={},
        request=request,
    )

    return MessageResponse(message=message)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Get user by ID (admin only)"""
    user = db.query(User).filter_by(id=user_id, facility_slug=current_user.facility_slug).first()
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
        facility_id=str(user.facility_id) if user.facility_id else None,
        facility_slug=user.facility_slug,
        branch_id=user.branch_id or user.department_id,
        branch_ids=user.branch_ids or user.departments or [],
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
    user = db.query(User).filter_by(id=user_id, facility_slug=current_user.facility_slug).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = activate
    user.save()

    action = "activated" if activate else "deactivated"
    return MessageResponse(message=f"User {action} successfully")
