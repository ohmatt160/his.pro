from typing import Optional

from pydantic import BaseModel, Field


class AlertCreate(BaseModel):
    facility_slug: Optional[str] = Field(None)  # if None, use user's facility
    alert_type: str = Field(..., pattern="^(info|warning|critical)$")
    title: str = Field(..., max_length=200)
    message: str = Field(...)
    recipient_id: Optional[str] = Field(None)
    expires_at: Optional[str] = Field(None)  # ISO datetime string


class RoleAlertCreate(BaseModel):
    alert_type: str = Field(..., pattern="^(info|warning|critical)$")
    title: str = Field(..., max_length=200)
    message: str = Field(...)
    recipient_role: str = Field(..., pattern="^(ADMIN|DOCTOR|NURSE|LAB_TECH|PHARMACIST|RECEPTIONIST|RADIOLOGIST)$")
    expires_at: Optional[str] = Field(None)


class AlertUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    message: Optional[str] = Field(None)
    alert_type: Optional[str] = Field(None, pattern="^(info|warning|critical)$")


class AlertResponse(BaseModel):
    id: str
    facility_slug: str
    alert_type: str
    title: str
    message: str
    recipient_id: Optional[str]
    recipient_name: Optional[str]
    is_read: bool
    read_at: Optional[str]
    expires_at: Optional[str]
    created_at: str



