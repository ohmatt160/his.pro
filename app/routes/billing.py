"""
Billing Routes - FastAPI Version
Converted from Flask-RESTx billing_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import logging

from app.extensions import get_db, db_session
from app.schemas.billing import InvoiceResponse, PaymentCreate, PaymentResponse, InvoiceCreate, InvoiceUpdate
from app.services.billing_service import BillingService
from app.services.patient_notification_service import PatientNotificationService
from app.services.receipt_service import ReceiptService
from app.utils.dependencies import get_current_user, role_required
from app.models.user import User
from app.models.patient import Patient
from app.models.billing import Payment
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
    has_receipt = bool(payment.receipt_filename)
    return PaymentResponse(
        id=str(payment.id),
        invoice_id=str(payment.invoice_id),
        amount=float(payment.amount or 0),
        payment_method=payment.payment_method,
        reference=payment.reference_number,
        notes=payment.notes,
        processed_by=None,
        has_receipt=has_receipt,
        receipt_original_name=payment.receipt_original_name,
        receipt_content_type=payment.receipt_content_type,
        receipt_size=payment.receipt_size,
        receipt_uploaded_at=payment.receipt_uploaded_at.isoformat() if payment.receipt_uploaded_at else None,
        receipt_url=f"/billing/payments/{payment.id}/receipt" if has_receipt else None,
        created_at=payment.payment_date.isoformat() if payment.payment_date else ""
    )


def _get_payment_for_facility(payment_id: str, facility_slug: str) -> Payment:
    payment = db_session.query(Payment).filter_by(id=payment_id).first()
    if not payment or not payment.invoice or payment.invoice.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


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
            return []
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
    PatientNotificationService.create(
        facility_slug=facility_slug,
        patient=patient,
        notification_type="bill_created",
        title="Bill created",
        message=f"Your bill {invoice.invoice_number} has been created.",
        source_type="invoice",
        source_id=invoice.id,
        metadata={"invoice_number": invoice.invoice_number, "amount": float(invoice.total or 0)},
    )

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

    invoice = payment.invoice
    patient = db_session.query(Patient).filter_by(
        id=invoice.patient_id,
        facility_slug=facility_slug,
    ).first()
    if patient:
        PatientNotificationService.create(
            facility_slug=facility_slug,
            patient=patient,
            notification_type="payment_received",
            title="Payment received",
            message=f"Payment of {float(payment.amount or 0):,.2f} was received for {invoice.invoice_number}.",
            source_type="payment",
            source_id=payment.id,
            metadata={
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "amount": float(payment.amount or 0),
                "payment_method": payment.payment_method,
            },
        )

    return _payment_response(payment)


@router.get("/invoices/{invoice_id}/payments", response_model=List[PaymentResponse])
async def get_invoice_payments(
    invoice_id: str,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST', 'NURSE')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    invoice = BillingService.get_invoice_by_id(invoice_id)

    if not invoice or invoice.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return [_payment_response(payment) for payment in invoice.payments]


@router.post("/payments/{payment_id}/receipt", response_model=PaymentResponse)
async def upload_payment_receipt(
    payment_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(role_required('ADMIN', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    payment = _get_payment_for_facility(payment_id, facility_slug)
    updated = await ReceiptService.attach_receipt(payment, file)
    return _payment_response(updated)


@router.get("/payments/{payment_id}/receipt")
async def download_payment_receipt(
    payment_id: str,
    current_user: User = Depends(role_required('ADMIN', 'RECEPTIONIST', 'DOCTOR', 'NURSE')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    payment = _get_payment_for_facility(payment_id, facility_slug)
    path = ReceiptService.get_receipt_file(payment)
    return FileResponse(
        path,
        media_type=payment.receipt_content_type or "application/octet-stream",
        filename=payment.receipt_original_name or "receipt",
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

    updated_invoice = BillingService.update_invoice(invoice, data.model_dump(exclude_unset=True))

    return _invoice_response(updated_invoice)
