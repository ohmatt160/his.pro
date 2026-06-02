from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class SupplierCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    contact_person: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = Field(None)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None)


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    contact_person: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = Field(None)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None)
    is_active: Optional[bool] = Field(None)


class SupplierResponse(BaseModel):
    id: str
    facility_slug: str
    name: str
    contact_person: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    is_active: bool
    created_at: str
    updated_at: Optional[str]
