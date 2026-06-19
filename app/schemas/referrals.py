from typing import Optional, Literal

from pydantic import BaseModel, Field


class ReferralCreate(BaseModel):
    patient_id: str = Field(..., max_length=36)
    to_department_id: str = Field(..., max_length=36)
    reason: str = Field(..., min_length=2, max_length=255)
    priority: Literal["routine", "urgent", "emergency"] = "routine"
    notes: Optional[str] = None


class ReferralResponse(BaseModel):
    id: str
    facility_slug: str
    patient_id: str
    from_department_id: Optional[str]
    to_department_id: str
    reason: str
    priority: str
    notes: Optional[str]
    status: str
    created_by: str
    accepted_by: Optional[str]
    completed_by: Optional[str]
    created_at: str
    updated_at: Optional[str]
    accepted_at: Optional[str]
    completed_at: Optional[str]
