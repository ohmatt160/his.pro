"""
Password Reset Routes - FastAPI Version
Converted from Flask-RESTx password_reset_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr
import logging

from app.extensions import get_db
from app.services.password_reset_service import PasswordResetService
from app.utils.dependencies import get_current_user, optional_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/password-reset", tags=["password-reset"])


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(...)
    new_password: str = Field(..., min_length=8)


class MessageResponse(BaseModel):
    message: str


@router.post("/forgot", response_model=MessageResponse)
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Request password reset - sends reset email"""
    success, message = PasswordResetService.request_password_reset(data.email)

    # Always return success to prevent email enumeration
    return MessageResponse(message="If an account exists with that email, a password reset link has been sent.")


@router.post("/confirm", response_model=MessageResponse)
async def confirm_password_reset(
    data: ResetPasswordRequest
):
    """Confirm password reset with token"""
    success, message = PasswordResetService.reset_password(data.token, data.new_password)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return MessageResponse(message="Password has been reset successfully")


@router.post("/change", response_model=MessageResponse)
async def change_password_authenticated(
    current_password: str = Field(...),
    new_password: str = Field(..., min_length=8),
    current_user: User = Depends(get_current_user)
):
    """Change password for authenticated user"""
    from app.services.user_profile_service import UserProfileService

    success, error = UserProfileService.change_password(current_user, current_password, new_password)
    if not success:
        raise HTTPException(status_code=400, detail=error)

    return MessageResponse(message="Password changed successfully")
