import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from app.models.billing import Invoice, InvoiceItem, Payment, InsuranceProvider, InsuranceClaim
from app.extensions import db, db_session


class BillingIdempotencyConflictError(Exception):
    pass


class BillingValidationError(Exception):
    pass

class BillingService:
    """Billing service class"""
    
    @staticmethod
    def generate_invoice_number():
        """Generate unique invoice number"""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        return f"INV-{timestamp}-{uuid.uuid4().hex[:6].upper()}"
    
    @staticmethod
    def generate_claim_number():
        """Generate unique claim number"""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        return f"CLM-{timestamp}-{uuid.uuid4().hex[:6].upper()}"

    @staticmethod
    def _parse_date(value):
        if not value:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        return datetime.fromisoformat(str(value)).date()

    @staticmethod
    def _parse_datetime(value):
        if not value:
            return datetime.utcnow()
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))
    
    # ==================== Invoices ====================
    
    @staticmethod
    def create_invoice(
        data,
        facility_slug=None,
        facility_id=None,
        branch_id=None,
        department_id=None,
        idempotency_key=None,
        payload_hash=None,
    ):
        """Create a new invoice with optional line items."""
        existing = None
        if idempotency_key:
            existing = Invoice.query.filter_by(
                facility_slug=facility_slug,
                idempotency_key=idempotency_key,
            ).first()
        if existing:
            if existing.idempotency_payload_hash != payload_hash:
                raise BillingIdempotencyConflictError
            return existing, False

        amount = Decimal(str(data.get('amount', 0)))
        invoice = Invoice(
            patient_id=data['patient_id'],
            invoice_number=BillingService.generate_invoice_number(),
            tax=data.get('tax', 0),
            discount=data.get('discount', 0),
            notes=data.get('notes'),
            due_date=BillingService._parse_date(data.get('due_date')),
            invoice_date=BillingService._parse_datetime(data.get('invoice_date')),
            facility_id=facility_id,
            facility_slug=facility_slug,
            branch_id=branch_id or department_id,
            department_id=department_id or branch_id,
            idempotency_key=idempotency_key,
            idempotency_payload_hash=payload_hash,
        )
        try:
            db_session.add(invoice)
            db_session.flush()

            items = data.get('items') or []
            if not items and amount > 0:
                items = [{
                    'description': data.get('description') or 'Clinical services',
                    'quantity': 1,
                    'unit_price': amount,
                }]

            for item_data in items:
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=item_data['description'],
                    quantity=item_data.get('quantity', 1),
                    unit_price=item_data.get('unit_price', 0)
                )
                item.calculate_total()
                db_session.add(item)

            db_session.flush()
            invoice.calculate_total()
            db_session.commit()
        except IntegrityError:
            db_session.rollback()
            if idempotency_key:
                existing = Invoice.query.filter_by(
                    facility_slug=facility_slug,
                    idempotency_key=idempotency_key,
                ).first()
                if existing:
                    if existing.idempotency_payload_hash != payload_hash:
                        raise BillingIdempotencyConflictError
                    return existing, False
            raise
        except Exception:
            db_session.rollback()
            raise

        db_session.refresh(invoice)
        return invoice, True
    
    @staticmethod
    def get_invoice_by_id(invoice_id):
        """Get invoice by ID"""
        return Invoice.query.get(invoice_id)
    
    @staticmethod
    def get_invoices_by_patient(patient_id):
        """Get all invoices for a patient"""
        return Invoice.query.filter_by(patient_id=patient_id).order_by(Invoice.invoice_date.desc()).all()
    
    @staticmethod
    def get_pending_invoices():
        """Get all pending invoices"""
        return Invoice.query.filter(Invoice.status.in_(['PENDING', 'PARTIAL'])).order_by(Invoice.invoice_date).all()
    
    @staticmethod
    def update_invoice(invoice, data):
        """Update invoice"""
        if 'due_date' in data:
            data['due_date'] = BillingService._parse_date(data['due_date'])

        for key, value in data.items():
            if hasattr(invoice, key) and value is not None and key not in ['items', 'invoice_number']:
                setattr(invoice, key, value)
        
        if 'items' in data:
            # Remove old items and add new ones
            InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()
            for item_data in data['items']:
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=item_data['description'],
                    quantity=item_data.get('quantity', 1),
                    unit_price=item_data.get('unit_price', 0)
                )
                item.calculate_total()
                item.save()
        
        invoice.calculate_total()
        invoice.save()
        return invoice
    
    # ==================== Payments ====================
    
    @staticmethod
    def create_payment(
        invoice_id,
        data,
        facility_slug=None,
        idempotency_key=None,
        payload_hash=None,
    ):
        """Create a payment for an invoice"""
        existing = None
        if idempotency_key:
            existing = Payment.query.filter_by(
                invoice_id=invoice_id,
                idempotency_key=idempotency_key,
            ).first()
        if existing:
            if existing.idempotency_payload_hash != payload_hash:
                raise BillingIdempotencyConflictError
            return existing, False

        invoice = (
            db_session.query(Invoice)
            .filter(Invoice.id == invoice_id)
            .with_for_update()
            .first()
        )
        if not invoice:
            db_session.rollback()
            raise BillingValidationError("Invoice not found")
        if facility_slug and invoice.facility_slug != facility_slug:
            db_session.rollback()
            raise BillingValidationError("Invoice not found")
        if invoice.status == "CANCELLED":
            db_session.rollback()
            raise BillingValidationError("Cancelled invoices cannot receive payments")

        amount = Decimal(str(data['amount']))
        total_paid = (
            db_session.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(Payment.invoice_id == invoice_id)
            .scalar()
        )
        balance = max(Decimal(str(invoice.total or 0)) - Decimal(str(total_paid or 0)), Decimal("0"))
        if amount > balance:
            db_session.rollback()
            raise BillingValidationError("Payment cannot be greater than the invoice balance")
        
        payment = Payment(
            invoice_id=invoice_id,
            amount=amount,
            payment_method=data['payment_method'],
            reference_number=data.get('reference_number') or data.get('reference'),
            notes=data.get('notes'),
            payment_date=BillingService._parse_datetime(data.get('payment_date')),
            idempotency_key=idempotency_key,
            idempotency_payload_hash=payload_hash,
        )
        try:
            db_session.add(payment)
            db_session.flush()

            total_paid += amount

            if total_paid >= invoice.total:
                invoice.status = 'PAID'
                invoice.paid_date = datetime.utcnow()
            else:
                invoice.status = 'PARTIAL'

            db_session.add(invoice)
            db_session.commit()
        except IntegrityError:
            db_session.rollback()
            if idempotency_key:
                existing = Payment.query.filter_by(
                    invoice_id=invoice_id,
                    idempotency_key=idempotency_key,
                ).first()
                if existing:
                    if existing.idempotency_payload_hash != payload_hash:
                        raise BillingIdempotencyConflictError
                    return existing, False
            raise
        except Exception:
            db_session.rollback()
            raise

        db_session.refresh(payment)
        return payment, True
    
    @staticmethod
    def get_payments_by_invoice(invoice_id):
        """Get all payments for an invoice"""
        return Payment.query.filter_by(invoice_id=invoice_id).order_by(Payment.payment_date).all()
    
    # ==================== Insurance Providers ====================
    
    @staticmethod
    def create_insurance_provider(data):
        """Create a new insurance provider"""
        if InsuranceProvider.query.filter_by(code=data['code']).first():
            return None, "Insurance provider code already exists"
        
        provider = InsuranceProvider(
            name=data['name'],
            code=data['code'],
            contact_number=data.get('contact_number'),
            email=data.get('email'),
            address=data.get('address')
        )
        provider.save()
        return provider, None
    
    @staticmethod
    def get_all_insurance_providers(active_only=True):
        """Get all insurance providers"""
        query = InsuranceProvider.query
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(InsuranceProvider.name).all()
    
    # ==================== Insurance Claims ====================
    
    @staticmethod
    def create_insurance_claim(data):
        """Create a new insurance claim"""
        invoice = Invoice.query.get(data['invoice_id'])
        if not invoice:
            return None, "Invoice not found"
        
        claim = InsuranceClaim(
            invoice_id=data['invoice_id'],
            insurance_provider_id=data.get('insurance_provider_id'),
            policy_number=data.get('policy_number'),
            claim_number=BillingService.generate_claim_number(),
            claimed_amount=data.get('claimed_amount', invoice.total),
            claim_date=datetime.utcnow()
        )
        claim.save()
        
        return claim, None
    
    @staticmethod
    def get_claims_by_patient(patient_id):
        """Get all claims for a patient"""
        return InsuranceClaim.query.join(Invoice).filter(
            Invoice.patient_id == patient_id
        ).order_by(InsuranceClaim.claim_date.desc()).all()
    
    @staticmethod
    def update_claim_status(claim_id, status, approved_amount=None):
        """Update insurance claim status"""
        claim = InsuranceClaim.query.get(claim_id)
        if not claim:
            return None, "Claim not found"
        
        claim.status = status
        if approved_amount is not None:
            claim.approved_amount = approved_amount
        
        if status == 'APPROVED' or status == 'REJECTED':
            claim.settlement_date = datetime.utcnow()
        
        claim.save()
        return claim
