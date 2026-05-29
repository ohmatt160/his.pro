from typing import Optional, List

from pydantic import BaseModel, Field


class MedicalRecordCreate(BaseModel):
    patient_id: str = Field(...)
    record_type: str = Field(..., pattern="^(CONSULTATION|LAB_RESULT|IMAGING|PRESCRIPTION|PROCEDURE|NOTE|VACCINATION)$")
    title: str = Field(..., max_length=200)
    description: Optional[str] = Field(None)
    data: Optional[dict] = Field(default_factory=dict)
    attachments: Optional[List[str]] = Field(default_factory=list)


class MedicalRecordUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None)
    data: Optional[dict] = None
    attachments: Optional[List[str]] = None


class MedicalRecordResponse(BaseModel):
    id: str
    patient_id: str
    record_type: str
    title: str
    description: Optional[str]
    data: Optional[dict]
    attachments: Optional[List[str]]
    created_by: str
    facility_slug: Optional[str]
    created_at: str
    updated_at: Optional[str]


