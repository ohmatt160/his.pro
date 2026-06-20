from typing import Optional, List

from pydantic import BaseModel, Field, EmailStr


# Pydantic models for request/response
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = Field(..., pattern="^(ADMIN|BRANCH_ADMIN|DOCTOR|NURSE|LAB_TECH|PHARMACIST|RECEPTIONIST|admin|branch_admin|doctor|nurse|lab_tech|pharmacist|receptionist)$")
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
    department_id: Optional[str] = None
    departments: List[str] = []
    branch_id: Optional[str] = None
    branch_ids: List[str] = []
    facility_id: Optional[str] = None
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


class UserSessionResponse(BaseModel):
    id: str
    user_agent: Optional[str]
    ip_address: Optional[str]
    last_seen_at: str
    expires_at: str
    is_current: bool


class FacilityStaffCreate(BaseModel):
    fullName: str = Field(..., min_length=2, max_length=200)
    role: str = Field(..., pattern="^(branch_admin|doctor|nurse|reception|pharmacist|lab|BRANCH_ADMIN|DOCTOR|NURSE|RECEPTIONIST|PHARMACIST|LAB_TECH)$")
    department: str = Field(..., min_length=2, max_length=100)
    departmentId: Optional[str] = Field(None, max_length=36)
    departmentIds: List[str] = Field(default_factory=list)
    branchId: Optional[str] = Field(None, max_length=36)
    branchIds: List[str] = Field(default_factory=list)
    email: Optional[EmailStr] = Field(None)
    phone: Optional[str] = Field(None, max_length=20)
    password: Optional[str] = Field(None, min_length=8)
    createdBy: Optional[str] = Field(None, max_length=200)


class FacilityStaffUpdate(BaseModel):
    fullName: Optional[str] = Field(None, min_length=2, max_length=200)
    role: Optional[str] = Field(None, pattern="^(branch_admin|doctor|nurse|reception|pharmacist|lab|BRANCH_ADMIN|DOCTOR|NURSE|RECEPTIONIST|PHARMACIST|LAB_TECH)$")
    department: Optional[str] = Field(None, min_length=2, max_length=100)
    departmentId: Optional[str] = Field(None, max_length=36)
    departmentIds: Optional[List[str]] = None
    branchId: Optional[str] = Field(None, max_length=36)
    branchIds: Optional[List[str]] = None
    email: Optional[EmailStr] = Field(None)
    phone: Optional[str] = Field(None, max_length=20)
    password: Optional[str] = Field(None, min_length=8)
    mustChangePassword: Optional[bool] = None
    isActive: Optional[bool] = None


class FacilityStaffResponse(BaseModel):
    staffRecordId: str
    facilityId: Optional[str] = None
    facilitySlug: str
    fullName: str
    role: str
    department: str
    departmentId: Optional[str] = None
    departmentIds: List[str] = []
    branchId: Optional[str] = None
    branchIds: List[str] = []
    email: str
    phone: str
    loginId: str
    password: str = ""
    temporaryPassword: str = ""
    mustChangePassword: bool
    status: str
    createdAt: str
    createdBy: Optional[str] = None

