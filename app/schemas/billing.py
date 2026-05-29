from typing import Optional

from pydantic import BaseModel, Field

class InvoiceCreate(BaseModel):
    patient_id: str = Field(...)
    amount: float = Field(..., gt=0)
    due_date: str = Field(...)
    notes: Optional[str] = Field(None)


class InvoiceUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(DRAFT|ISSUED|PAID|OVERDUE|CANCELLED)$")
    notes: Optional[str] = Field(None)


class InvoiceResponse(BaseModel):
    id: str
    patient_id: str
    invoice_number: str
    amount: float
    paid_amount: float
    balance: float
    status: str
    due_date: str
    paid_date: Optional[str]
    notes: Optional[str]
    facility_slug: Optional[str]
    created_at: str
    updated_at: Optional[str]


class PaymentCreate(BaseModel):
    amount: float = Field(..., gt=0)
    payment_method: str = Field(..., pattern="^(CASH|CARD|INSURANCE|TRANSFER)$")
    reference: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None)


class PaymentResponse(BaseModel):
    id: str
    invoice_id: str
    amount: float
    payment_method: str
    reference: Optional[str]
    notes: Optional[str]
    processed_by: Optional[str]
    created_at: str

