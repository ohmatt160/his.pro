from typing import Optional

from pydantic import BaseModel, Field

class AppointmentCreate(BaseModel):
    patient_id: str = Field(...)
    doctor_id: str = Field(...)
    appointment_date: str = Field(...)
    reason: Optional[str] = Field(None)
    notes: Optional[str] = Field(None)


class AppointmentUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(SCHEDULED|CONFIRMED|IN_PROGRESS|COMPLETED|CANCELLED|NO_SHOW)$")
    reason: Optional[str] = Field(None)
    notes: Optional[str] = Field(None)


class AppointmentResponse(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    appointment_date: str
    scheduled_time: Optional[str]
    duration_minutes: int
    status: str
    reason: Optional[str]
    notes: Optional[str]
    facility_slug: Optional[str]
    created_at: str
    updated_at: Optional[str]



