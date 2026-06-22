from typing import Optional, List

from pydantic import BaseModel, Field


class MedicationCreate(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50)
    generic_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None)
    category: Optional[str] = Field(None, max_length=50)
    unit: Optional[str] = Field(None, max_length=20)
    strength: Optional[str] = Field(None, max_length=50)
    price: Optional[float] = Field(None, ge=0)
    reorder_level: Optional[int] = Field(None, ge=0)


class InventoryResponse(BaseModel):
    id: str
    medication_id: str
    quantity: int
    expiry_date: Optional[str]
    batch_number: Optional[str]
    location: Optional[str]
    last_updated: str


class MedicationResponse(BaseModel):
    id: str
    name: str
    code: str
    generic_name: Optional[str]
    description: Optional[str]
    category: Optional[str]
    unit: Optional[str]
    strength: Optional[str]
    price: Optional[float]
    reorder_level: Optional[int]
    is_active: bool
    facility_slug: Optional[str]
    inventory: Optional[InventoryResponse] = None
    created_at: str
    updated_at: Optional[str]


class InventoryCreate(BaseModel):
    quantity: int = Field(..., ge=0)
    expiry_date: Optional[str] = Field(None)
    batch_number: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=100)


class PrescriptionItemCreate(BaseModel):
    medication_id: str = Field(...)
    quantity: int = Field(..., gt=0)
    dosage: Optional[str] = Field(None)
    instructions: Optional[str] = Field(None)


class PrescriptionCreate(BaseModel):
    patient_id: str = Field(...)
    items: List[PrescriptionItemCreate] = Field(..., min_items=1)
    notes: Optional[str] = Field(None)
    department_id: Optional[str] = Field(None, max_length=36)
    branch_id: Optional[str] = Field(None, max_length=36)


class PrescriptionResponse(BaseModel):
    id: str
    patient_id: str
    prescribed_by: str
    status: str
    notes: Optional[str]
    filled_by: Optional[str]
    filled_at: Optional[str]
    facility_slug: Optional[str]
    department_id: Optional[str] = None
    branch_id: Optional[str] = None
    created_at: str
    updated_at: Optional[str]


