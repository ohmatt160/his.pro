"""
Billing Routes - FastAPI Version
Converted from Flask-RESTx billing_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import logging

from app.extensions import get_db, db_session
from app.schemas.billing import InvoiceResponse, PaymentCreate, PaymentResponse, InvoiceCreate, InvoiceUpdate
from app.services.billing_service import BillingService
from app.utils.dependencies import get_current_user, role_required
from app.models.user import User
from app.models.patient import Patient
from app.models.facility import Facility

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])


def _invoice_response(invoice) -> InvoiceResponse:
    paid_amount = sum(float(payment.amount or 0) for payment in invoice.payments)
    amount = float(invoice.total or 0)
    balance = max(amount - paid_amount, 0)

    return InvoiceResponse(
        id=str(invoice.id),
        patient_id=str(invoice.patient_id),
        invoice_number=invoice.invoice_number,
        amount=amount,
        paid_amount=paid_amount,
        balance=balance,
        status=invoice.status,
        due_date=invoice.due_date.isoformat() if invoice.due_date else "",
        paid_date=invoice.paid_date.isoformat() if invoice.paid_date else None,
        notes=invoice.notes,
        facility_slug=invoice.facility_slug,
        created_at=invoice.created_at.isoformat() if invoice.created_at else "",
        updated_at=invoice.updated_at.isoformat() if invoice.updated_at else None
    )


def _payment_response(payment) -> PaymentResponse:
    return PaymentResponse(
        id=str(payment.id),
        invoice_id=str(payment.invoice_id),
        amount=float(payment.amount or 0),
        payment_method=payment.payment_method,
        reference=payment.reference_number,
        notes=payment.notes,
        processed_by=None,
        created_at=payment.payment_date.isoformat() if payment.payment_date else ""
    )


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

    return [_invoice_response(i) for i in invoices]


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

    invoice = BillingService.create_invoice(data.model_dump(), facility_slug=facility_slug)

    return _invoice_response(invoice)


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

    return _invoice_response(invoice)


@router.post("/invoices/{invoice_id}/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def add_payment(
    invoice_id: str,
    data: PaymentCreate,
    current_user: User = Depends(role_required('ADMIN', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    payment, error = BillingService.create_payment(
        invoice_id,
        data.model_dump(),
        facility_slug=facility_slug,
    )

    if not payment:
        raise HTTPException(status_code=404, detail=error or "Invoice not found or payment error")

    return _payment_response(payment)


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

    updated_invoice = BillingService.update_invoice(invoice, data.model_dump(exclude_unset=True))

    return _invoice_response(updated_invoice)
