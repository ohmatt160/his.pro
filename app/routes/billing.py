"""
Billing Routes - FastAPI Version
Converted from Flask-RESTx billing_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from app.extensions import get_db
from app.services.billing_service import BillingService
from app.utils.dependencies import get_current_user, role_required
from app.models.user import User
from app.models.patient import Patient
from app.models.facility import Facility

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])


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


class MessageResponse(BaseModel):
    message: str


@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_invoices(
    patient_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST', 'NURSE')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    from app.models.billing import Invoice
    query = db_session.query(Invoice).filter_by(facility_slug=facility_slug)

    if patient_id:
        # Verify patient belongs to facility
        patient = db_session.query(Patient).filter_by(id=patient_id, facility_slug=facility_slug).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        query = query.filter_by(patient_id=patient_id)
    elif status:
        query = query.filter_by(status=status)

    invoices = query.order_by(Invoice.invoice_date.desc()).all()

    return [
        InvoiceResponse(
            id=str(i.id),
            patient_id=str(i.patient_id),
            invoice_number=i.invoice_number,
            amount=float(i.amount) if i.amount else 0.0,
            paid_amount=float(i.paid_amount) if i.paid_amount else 0.0,
            balance=float(i.balance) if i.balance else 0.0,
            status=i.status,
            due_date=i.due_date.isoformat() if i.due_date else "",
            paid_date=i.paid_date.isoformat() if i.paid_date else None,
            notes=i.notes,
            facility_slug=i.facility_slug,
            created_at=i.created_at.isoformat() if i.created_at else "",
            updated_at=i.updated_at.isoformat() if i.updated_at else None
        ) for i in invoices
    ]


@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: InvoiceCreate,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    # Verify patient belongs to facility
    patient = db.query(Patient).filter_by(id=data.patient_id, facility_slug=facility_slug).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    invoice = BillingService.create_invoice(data.dict(), facility_slug=facility_slug)

    return InvoiceResponse(
        id=str(invoice.id),
        patient_id=str(invoice.patient_id),
        invoice_number=invoice.invoice_number,
        amount=invoice.amount,
        paid_amount=invoice.paid_amount,
        balance=invoice.balance,
        status=invoice.status,
        due_date=invoice.due_date.isoformat() if invoice.due_date else "",
        paid_date=invoice.paid_date.isoformat() if invoice.paid_date else None,
        notes=invoice.notes,
        facility_slug=invoice.facility_slug,
        created_at=invoice.created_at.isoformat() if invoice.created_at else "",
        updated_at=invoice.updated_at.isoformat() if invoice.updated_at else None
    )


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST', 'NURSE')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    invoice = BillingService.get_invoice_by_id(invoice_id)

    if not invoice or invoice.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return InvoiceResponse(
        id=str(invoice.id),
        patient_id=str(invoice.patient_id),
        invoice_number=invoice.invoice_number,
        amount=invoice.amount,
        paid_amount=invoice.paid_amount,
        balance=invoice.balance,
        status=invoice.status,
        due_date=invoice.due_date.isoformat() if invoice.due_date else "",
        paid_date=invoice.paid_date.isoformat() if invoice.paid_date else None,
        notes=invoice.notes,
        facility_slug=invoice.facility_slug,
        created_at=invoice.created_at.isoformat() if invoice.created_at else "",
        updated_at=invoice.updated_at.isoformat() if invoice.updated_at else None
    )


@router.post("/invoices/{invoice_id}/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def add_payment(
    invoice_id: str,
    data: PaymentCreate,
    current_user: User = Depends(role_required('ADMIN', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    payment = BillingService.add_payment(invoice_id, data.dict(), current_user.id, facility_slug)

    if not payment:
        raise HTTPException(status_code=404, detail="Invoice not found or payment error")

    return PaymentResponse(
        id=str(payment.id),
        invoice_id=str(payment.invoice_id),
        amount=payment.amount,
        payment_method=payment.payment_method,
        reference=payment.reference,
        notes=payment.notes,
        processed_by=str(payment.processed_by) if payment.processed_by else None,
        created_at=payment.created_at.isoformat() if payment.created_at else ""
    )


@router.put("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: str,
    data: InvoiceUpdate,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    invoice = BillingService.get_invoice_by_id(invoice_id)

    if not invoice or invoice.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Invoice not found")

    updated_invoice = BillingService.update_invoice(invoice, data.dict(exclude_unset=True))

    return InvoiceResponse(
        id=str(updated_invoice.id),
        patient_id=str(updated_invoice.patient_id),
        invoice_number=updated_invoice.invoice_number,
        amount=updated_invoice.amount,
        paid_amount=updated_invoice.paid_amount,
        balance=updated_invoice.balance,
        status=updated_invoice.status,
        due_date=updated_invoice.due_date.isoformat() if updated_invoice.due_date else "",
        paid_date=updated_invoice.paid_date.isoformat() if updated_invoice.paid_date else None,
        notes=updated_invoice.notes,
        facility_slug=updated_invoice.facility_slug,
        created_at=updated_invoice.created_at.isoformat() if updated_invoice.created_at else "",
        updated_at=updated_invoice.updated_at.isoformat() if updated_invoice.updated_at else None
    )
