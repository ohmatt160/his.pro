from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field


class BranchCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=160)
    location: Optional[str] = Field(None, max_length=240)
    address: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=30)
    email: Optional[EmailStr] = None
    modules: List[str] = Field(default_factory=list)
    settings: dict = Field(default_factory=dict)


class BranchUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=160)
    location: Optional[str] = Field(None, max_length=240)
    address: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=30)
    email: Optional[EmailStr] = None
    modules: Optional[List[str]] = None
    settings: Optional[dict] = None
    is_public: Optional[bool] = None
    is_active: Optional[bool] = None


class BranchModulesUpdate(BaseModel):
    modules: List[str] = Field(default_factory=list)


class BranchResponse(BaseModel):
    id: str
    facility_id: str
    facility_slug: str
    name: str
    slug: str
    location: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    modules: List[str] = Field(default_factory=list)
    settings: dict = Field(default_factory=dict)
    is_public: bool = False
    is_active: bool = True
    login_url_path: str
    dashboard_url_path: str
    created_at: str
    updated_at: Optional[str] = None
