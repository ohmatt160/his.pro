from typing import Optional, List

from pydantic import BaseModel, Field


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
    modules: List[str]
    settings: dict
    is_active: bool
    created_at: str
    updated_at: Optional[str]

