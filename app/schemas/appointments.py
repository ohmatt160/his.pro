from typing import Optional

from pydantic import BaseModel, Field

class AppointmentCreate(BaseModel):
    patient_id: str = Field(...)
    doctor_id: str = Field(...)
    appointment_date: str = Field(...)
    duration_minutes: int = Field(30, ge=5, le=480)
    reason: Optional[str] = Field(None)
    notes: Optional[str] = Field(None)
    department_id: Optional[str] = Field(None, max_length=36)


class AppointmentUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(SCHEDULED|CONFIRMED|IN_PROGRESS|COMPLETED|CANCELLED|NO_SHOW)$")
    appointment_date: Optional[str] = Field(None)
    duration_minutes: Optional[int] = Field(None, ge=5, le=480)
    reason: Optional[str] = Field(None)
    notes: Optional[str] = Field(None)
    department_id: Optional[str] = Field(None, max_length=36)


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
    department_id: Optional[str] = None
    created_at: str
    updated_at: Optional[str]



