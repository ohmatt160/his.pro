from typing import Optional

from pydantic import BaseModel, Field, EmailStr


# Pydantic models for request/response
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = Field(..., pattern="^(ADMIN|DOCTOR|NURSE|LAB_TECH|PHARMACIST|RECEPTIONIST|admin|doctor|nurse|lab_tech|pharmacist|receptionist)$")
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    facility_slug: Optional[str] = Field(None, max_length=100)


class UserLogin(BaseModel):
    username: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str] = None
    facility_slug: Optional[str]
    is_active: bool
    created_at: str
    updated_at: Optional[str]

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = Field(None)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)

class MessageResponse(BaseModel):
    message: str


class FacilityStaffCreate(BaseModel):
    fullName: str = Field(..., min_length=2, max_length=200)
    role: str = Field(..., pattern="^(doctor|nurse|reception|pharmacist|lab|DOCTOR|NURSE|RECEPTIONIST|PHARMACIST|LAB_TECH)$")
    department: str = Field(..., min_length=2, max_length=100)
    email: Optional[EmailStr] = Field(None)
    phone: Optional[str] = Field(None, max_length=20)
    password: Optional[str] = Field(None, min_length=8)
    createdBy: Optional[str] = Field(None, max_length=200)


class FacilityStaffResponse(BaseModel):
    staffRecordId: str
    facilitySlug: str
    fullName: str
    role: str
    department: str
    email: str
    phone: str
    loginId: str
    password: str = ""
    temporaryPassword: str = ""
    mustChangePassword: bool
    status: str
    createdAt: str
    createdBy: Optional[str] = None
