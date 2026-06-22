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
from app.utils.branch_scope import (
    effective_branch_id,
    ensure_patient_branch_access,
    require_facility_slug,
    require_tenant_row,
    tenant_query,
)
from app.models.user import User
from app.models.patient import Patient
from app.models.billing import Invoice, Payment
from app.models.facility import Facility

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])


def _invoice_response(invoice, payments=None) -> InvoiceResponse:
    invoice_payments = payments if payments is not None else invoice.payments
    paid_amount = sum(float(payment.amount or 0) for payment in invoice_payments)
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
        branch_id=invoice.branch_id or invoice.department_id,
        department_id=invoice.department_id,
        payments=[_payment_response(payment) for payment in invoice_payments],
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


def _get_payment_for_user(payment_id: str, current_user: User) -> Payment:
    payment = db_session.query(Payment).filter_by(id=payment_id).first()
    if not payment or not payment.invoice:
        raise HTTPException(status_code=404, detail="Payment not found")
    require_tenant_row(payment.invoice, current_user, "Payment not found")
    return payment


@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_invoices(
    patient_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None, max_length=36),
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'RECEPTIONIST', 'NURSE')),
    db: Session = Depends(get_db)
):
    facility_slug = require_facility_slug(current_user)
    query = tenant_query(db_session, Invoice, current_user, branch_id)

    if patient_id:
        # Verify patient belongs to facility
        patient = db_session.query(Patient).filter_by(id=patient_id, facility_slug=facility_slug).first()
        if not patient:
            return []
        ensure_patient_branch_access(patient, current_user, branch_id)
        query = query.filter_by(patient_id=patient_id)
    elif status:
        query = query.filter_by(status=status)

    invoices = query.order_by(Invoice.invoice_date.desc()).all()
    invoice_ids = [invoice.id for invoice in invoices]
    payments_by_invoice_id = {invoice_id: [] for invoice_id in invoice_ids}
    if invoice_ids:
        payments = (
            db_session.query(Payment)
            .join(Invoice, Invoice.id == Payment.invoice_id)
            .filter(
                Payment.invoice_id.in_(invoice_ids),
                Invoice.facility_slug == facility_slug,
            )
            .order_by(Payment.payment_date.desc())
            .all()
        )
        for payment in payments:
            payments_by_invoice_id.setdefault(payment.invoice_id, []).append(payment)

    return [_invoice_response(i, payments_by_invoice_id.get(i.id, [])) for i in invoices]


@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: InvoiceCreate,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    facility_slug = require_facility_slug(current_user)

    # Verify patient belongs to facility
    patient = db.query(Patient).filter_by(id=data.patient_id, facility_slug=facility_slug).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    branch_id = ensure_patient_branch_access(patient, current_user)

    invoice = BillingService.create_invoice(
        data.model_dump(),
        facility_slug=facility_slug,
        branch_id=branch_id or patient.branch_id or patient.department_id,
        department_id=branch_id or patient.department_id,
    )
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
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'RECEPTIONIST', 'NURSE')),
    db: Session = Depends(get_db)
):
    invoice = BillingService.get_invoice_by_id(invoice_id)
    require_tenant_row(invoice, current_user, "Invoice not found")

    return _invoice_response(invoice)


@router.post("/invoices/{invoice_id}/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def add_payment(
    invoice_id: str,
    data: PaymentCreate,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    facility_slug = require_facility_slug(current_user)
    invoice = BillingService.get_invoice_by_id(invoice_id)
    require_tenant_row(invoice, current_user, "Invoice not found")
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
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'RECEPTIONIST', 'NURSE')),
    db: Session = Depends(get_db)
):
    invoice = BillingService.get_invoice_by_id(invoice_id)
    require_tenant_row(invoice, current_user, "Invoice not found")

    return [_payment_response(payment) for payment in invoice.payments]


@router.post("/payments/{payment_id}/receipt", response_model=PaymentResponse)
async def upload_payment_receipt(
    payment_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    payment = _get_payment_for_user(payment_id, current_user)
    updated = await ReceiptService.attach_receipt(payment, file)
    return _payment_response(updated)


@router.get("/payments/{payment_id}/receipt")
async def download_payment_receipt(
    payment_id: str,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'RECEPTIONIST', 'DOCTOR', 'NURSE')),
    db: Session = Depends(get_db)
):
    payment = _get_payment_for_user(payment_id, current_user)
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
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN')),
    db: Session = Depends(get_db)
):
    invoice = BillingService.get_invoice_by_id(invoice_id)
    require_tenant_row(invoice, current_user, "Invoice not found")

    updated_invoice = BillingService.update_invoice(invoice, data.model_dump(exclude_unset=True))

    return _invoice_response(updated_invoice)
