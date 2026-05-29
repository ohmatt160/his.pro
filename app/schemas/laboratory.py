from typing import Optional

from pydantic import BaseModel, Field


class LabTestCreate(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50)
    description: Optional[str] = Field(None)
    category: Optional[str] = Field(None, max_length=50)
    unit: Optional[str] = Field(None, max_length=20)
    reference_range: Optional[str] = Field(None)
    price: Optional[float] = Field(None, ge=0)


class LabTestResponse(BaseModel):
    id: str
    name: str
    code: str
    description: Optional[str]
    category: Optional[str]
    unit: Optional[str]
    reference_range: Optional[str]
    price: Optional[float]
    is_active: bool
    created_at: str
    updated_at: Optional[str]


class LabOrderCreate(BaseModel):
    patient_id: str = Field(...)
    test_id: str = Field(...)
    priority: Optional[str] = Field(None, pattern="^(ROUTINE|URGENT|STAT)$")
    notes: Optional[str] = Field(None)
    order_date: Optional[str] = Field(None)


class LabOrderUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(PENDING|COLLECTED|IN_PROGRESS|COMPLETED|CANCELLED)$")


class LabOrderResponse(BaseModel):
    id: str
    patient_id: str
    test_id: str
    ordered_by: str
    status: str
    priority: Optional[str]
    notes: Optional[str]
    completed_at: Optional[str]
    facility_slug: Optional[str]
    created_at: str
    updated_at: Optional[str]


class LabResultCreate(BaseModel):
    value: Optional[str] = Field(None)
    is_abnormal: Optional[bool] = Field(False)
    notes: Optional[str] = Field(None)


class LabResultResponse(BaseModel):
    id: str
    order_id: str
    entered_by: Optional[str]
    value: Optional[str]
    is_abnormal: Optional[bool]
    notes: Optional[str]
    created_at: str
    updated_at: Optional[str]

