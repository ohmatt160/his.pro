from typing import Optional, List, Literal

from pydantic import BaseModel, Field

from app.schemas.branches import BranchResponse


class FacilityCreate(BaseModel):
    name: str = Field(..., max_length=100)
    type: str = Field(..., max_length=50)
    country: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=120)
    modules: Optional[List[str]] = Field(default_factory=list)
    settings: Optional[dict] = Field(default_factory=dict)


class FacilityUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    type: Optional[str] = Field(None, max_length=50)
    country: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=120)
    settings: Optional[dict] = None


class FacilityModulesUpdate(BaseModel):
    modules: List[str] = Field(default_factory=list)


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    location: Optional[str] = Field(None, max_length=200)
    phone_extension: Optional[str] = Field(None, max_length=30)
    services: List[str] = Field(default_factory=list)
    is_visible: bool = False


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    location: Optional[str] = Field(None, max_length=200)
    phone_extension: Optional[str] = Field(None, max_length=30)
    services: Optional[List[str]] = None
    is_visible: Optional[bool] = None


class FacilitySettingsUpdate(BaseModel):
    hospital_type: Literal["single", "multi_clinic"]


class FacilityResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    slug: str
    type: str
    country: Optional[str]
    address: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    hospital_type: str = "single"
    departments: List[dict] = Field(default_factory=list)
    branches: List[BranchResponse] = Field(default_factory=list)
    modules: List[str]
    settings: dict
    is_active: bool
    created_at: str
    updated_at: Optional[str]

