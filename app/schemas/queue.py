from typing import List, Optional

from pydantic import BaseModel, Field


class QueueCreate(BaseModel):
    patient_id: str = Field(...)
    appointment_id: Optional[str] = Field(None)
    department: str = Field(..., max_length=100)
    branch_id: Optional[str] = Field(None, max_length=36)
    priority: Optional[str] = Field('normal', pattern="^(normal|urgent)$")


class QueueUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(waiting|in_progress|completed|no_show)$")
    priority: Optional[str] = Field(None, pattern="^(normal|urgent)$")
    department: Optional[str] = Field(None, max_length=100)
    branch_id: Optional[str] = Field(None, max_length=36)

class QueueResponse(BaseModel):
    # fields remain
    id: str
    patient_id: str
    patient_name: Optional[str]
    patient_phone: Optional[str]
    patient_date_of_birth: Optional[str]
    appointment_id: Optional[str]
    appointment_time: Optional[str]
    facility_slug: str
    department: str
    branch_id: Optional[str] = None
    status: str
    queue_number: int
    priority: str
    checked_in_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str

class QueueListResponse(BaseModel):
    queue_entries: List[QueueResponse]
    total: int
    page: int
    per_page: int
    pages: int


