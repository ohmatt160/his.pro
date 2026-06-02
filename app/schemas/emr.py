from typing import Optional, List

from pydantic import BaseModel, Field


class MedicalRecordCreate(BaseModel):
    patient_id: str = Field(...)
    appointment_id: Optional[str] = Field(None)
    chief_complaint: Optional[str] = Field(None)
    vital_signs: Optional[dict] = Field(default_factory=dict)
    symptoms: Optional[List[str]] = Field(default_factory=list)
    diagnosis: Optional[List[str]] = Field(default_factory=list)
    treatment_plan: Optional[str] = Field(None)
    prescriptions: Optional[List[dict]] = Field(default_factory=list)
    lab_orders: Optional[List[dict]] = Field(default_factory=list)
    follow_up_date: Optional[str] = Field(None)
    notes: Optional[str] = Field(None)


class MedicalRecordUpdate(BaseModel):
    chief_complaint: Optional[str] = Field(None)
    vital_signs: Optional[dict] = None
    symptoms: Optional[List[str]] = None
    diagnosis: Optional[List[str]] = None
    treatment_plan: Optional[str] = Field(None)
    prescriptions: Optional[List[dict]] = None
    lab_orders: Optional[List[dict]] = None
    follow_up_date: Optional[str] = Field(None)
    notes: Optional[str] = Field(None)


class MedicalRecordResponse(BaseModel):
    id: str
    patient_id: str
    appointment_id: Optional[str]
    chief_complaint: Optional[str]
    vital_signs: Optional[dict]
    symptoms: Optional[List[str]]
    diagnosis: Optional[List[str]]
    treatment_plan: Optional[str]
    prescriptions: Optional[List[dict]]
    lab_orders: Optional[List[dict]]
    follow_up_date: Optional[str]
    notes: Optional[str]
    created_by: str
    facility_slug: Optional[str]
    created_at: str
    updated_at: Optional[str]


