from typing import Optional

from pydantic import BaseModel, Field


class RadiologyCreate(BaseModel):
    patient_id: str = Field(...)
    facility_slug: Optional[str] = Field(None)
    modality: str = Field(..., pattern="^(X-ray|CT|MRI|Ultrasound)$")
    body_part: str = Field(..., max_length=100)
    clinical_notes: Optional[str] = Field(None)
    department_id: Optional[str] = Field(None, max_length=36)
    branch_id: Optional[str] = Field(None, max_length=36)


class RadiologyUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(pending|ordered|completed|cancelled)$")
    radiologist_id: Optional[str] = Field(None)
    clinical_notes: Optional[str] = Field(None)


class RadiologyReport(BaseModel):
    report: str = Field(...)


class RadiologyResponse(BaseModel):
    id: str
    patient_id: str
    facility_slug: str
    department_id: Optional[str] = None
    branch_id: Optional[str] = None
    modality: str
    body_part: str
    clinical_notes: Optional[str]
    status: str
    requested_by: str
    radiologist_id: Optional[str]
    report: Optional[str]
    report_date: Optional[str]
    request_date: str
    patient_name: Optional[str]
    requested_by_name: Optional[str]
    radiologist_name: Optional[str]

