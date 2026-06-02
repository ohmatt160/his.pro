from typing import Optional, List

from pydantic import BaseModel, Field


class ConsultationStart(BaseModel):
    patient_id: str = Field(...)
    appointment_id: Optional[str] = Field(None)
    chief_complaint: Optional[str] = Field(None, max_length=2000)


class ConsultationUpdate(BaseModel):
    chief_complaint: Optional[str] = Field(None, max_length=2000)
    vital_signs: Optional[dict] = None
    symptoms: Optional[List[str]] = None
    diagnosis: Optional[List[str]] = None
    treatment_plan: Optional[str] = Field(None, max_length=5000)
    prescriptions: Optional[List[dict]] = None
    lab_orders: Optional[List[dict]] = None
    radiology_orders: Optional[List[dict]] = None
    follow_up_date: Optional[str] = Field(None)
    notes: Optional[str] = Field(None, max_length=5000)


class ConsultationResponse(BaseModel):
    id: str
    patient_id: str
    patient_name: str
    appointment_id: Optional[str]
    appointment_status: Optional[str]
    chief_complaint: Optional[str]
    vital_signs: dict
    symptoms: List[str]
    diagnosis: List[str]
    treatment_plan: Optional[str]
    prescriptions: List[dict]
    lab_orders: List[dict]
    radiology_orders: List[dict]
    follow_up_date: Optional[str]
    notes: Optional[str]
    created_by: str
    facility_slug: str
    status: str
    created_at: str
    updated_at: Optional[str]
