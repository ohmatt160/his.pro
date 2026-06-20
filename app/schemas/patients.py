from typing import Optional, List

from pydantic import BaseModel, Field


# Pydantic models
class PatientCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: str = Field(...)  # ISO date string
    gender: Optional[str] = Field(None, pattern="^(MALE|FEMALE|OTHER)$")
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=120)
    address: Optional[str] = Field(None)
    blood_type: Optional[str] = Field(None, pattern="^(A\\+|A-|B\\+|B-|O\\+|O-|AB\\+|AB-)$")
    medical_history: Optional[dict] = Field(default_factory=dict)
    emergency_contact_name: Optional[str] = Field(None, max_length=100)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)
    department_id: Optional[str] = Field(None, max_length=36)
    branch_id: Optional[str] = Field(None, max_length=36)


class PatientUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    date_of_birth: Optional[str] = Field(None)
    gender: Optional[str] = Field(None, pattern="^(MALE|FEMALE|OTHER)$")
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=120)
    address: Optional[str] = Field(None)
    blood_type: Optional[str] = Field(None, pattern="^(A\\+|A-|B\\+|B-|O\\+|O-|AB\\+|AB-)$")
    medical_history: Optional[dict] = None
    emergency_contact_name: Optional[str] = Field(None, max_length=100)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)
    department_id: Optional[str] = Field(None, max_length=36)
    branch_id: Optional[str] = Field(None, max_length=36)


class PatientResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    date_of_birth: str
    gender: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    address: Optional[str]
    blood_type: Optional[str]
    medical_history: Optional[dict]
    emergency_contact_name: Optional[str]
    emergency_contact_phone: Optional[str]
    created_by: str
    facility_slug: Optional[str]
    department_id: Optional[str] = None
    branch_id: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: Optional[str]
    full_name: Optional[str]


class PatientListResponse(BaseModel):
    patients: List[PatientResponse]
    total: int
    page: int
    per_page: int
    pages: int


class PatientTimelineEvent(BaseModel):
    id: str
    event_type: str
    module: str
    title: str
    description: str
    status: Optional[str]
    occurred_at: str
    metadata: dict = Field(default_factory=dict)


class PatientTimelineResponse(BaseModel):
    patient: PatientResponse
    events: List[PatientTimelineEvent]
    total: int
