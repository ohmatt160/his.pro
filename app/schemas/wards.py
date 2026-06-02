from typing import List, Optional

from pydantic import BaseModel, Field


class WardBedCreate(BaseModel):
    ward_name: str = Field(..., min_length=1, max_length=120)
    bed_number: str = Field(..., min_length=1, max_length=40)
    status: str = Field("AVAILABLE", pattern="^(AVAILABLE|OCCUPIED|MAINTENANCE)$")
    notes: Optional[str] = Field(None, max_length=2000)


class WardBedUpdate(BaseModel):
    ward_name: Optional[str] = Field(None, min_length=1, max_length=120)
    bed_number: Optional[str] = Field(None, min_length=1, max_length=40)
    status: Optional[str] = Field(None, pattern="^(AVAILABLE|OCCUPIED|MAINTENANCE)$")
    notes: Optional[str] = Field(None, max_length=2000)


class WardBedResponse(BaseModel):
    id: str
    facility_slug: str
    ward_name: str
    bed_number: str
    status: str
    notes: Optional[str]
    created_at: str
    updated_at: Optional[str]


class WardAdmissionCreate(BaseModel):
    patient_id: str = Field(...)
    bed_id: Optional[str] = Field(None)
    ward_name: str = Field(..., min_length=1, max_length=120)
    reason: Optional[str] = Field(None, max_length=3000)
    acuity: str = Field("normal", pattern="^(normal|urgent)$")


class WardAdmissionUpdate(BaseModel):
    bed_id: Optional[str] = Field(None)
    ward_name: Optional[str] = Field(None, min_length=1, max_length=120)
    reason: Optional[str] = Field(None, max_length=3000)
    acuity: Optional[str] = Field(None, pattern="^(normal|urgent)$")
    status: Optional[str] = Field(None, pattern="^(ACTIVE|DISCHARGED|TRANSFERRED)$")


class NursingObservationCreate(BaseModel):
    vital_signs: Optional[dict] = None
    note: Optional[str] = Field(None, max_length=3000)
    medication_round: Optional[str] = Field(None, max_length=1000)


class WardAdmissionResponse(BaseModel):
    id: str
    facility_slug: str
    patient_id: str
    patient_name: str
    patient_phone: Optional[str]
    bed_id: Optional[str]
    bed_number: Optional[str]
    ward_name: str
    reason: Optional[str]
    acuity: str
    status: str
    observations: List[dict]
    nursing_notes: List[dict]
    admitted_by: str
    admitted_at: str
    discharged_at: Optional[str]
    created_at: str
    updated_at: Optional[str]
