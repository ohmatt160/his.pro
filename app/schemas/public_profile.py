from typing import List, Optional

from pydantic import BaseModel, Field


class PublicService(BaseModel):
    id: Optional[str] = Field(None, max_length=36)
    name: str = Field(..., min_length=2, max_length=160)
    price: Optional[float] = Field(None, ge=0)
    duration: Optional[str] = Field(None, max_length=80)
    description: Optional[str] = Field(None, max_length=500)


class PublicDepartmentProfile(BaseModel):
    id: str
    is_visible: bool = False
    services: List[PublicService] = Field(default_factory=list)
    staff_ids: List[str] = Field(default_factory=list)
    working_hours: Optional[dict] = Field(default_factory=dict)
    photos: List[str] = Field(default_factory=list)


class PublicProfileUpdate(BaseModel):
    is_public: bool = False
    display_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=120)
    photos: List[str] = Field(default_factory=list)
    departments: List[PublicDepartmentProfile] = Field(default_factory=list)
