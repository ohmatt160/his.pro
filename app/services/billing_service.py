import uuid
from datetime import datetime
from app.models.billing import Invoice, InvoiceItem, Payment, InsuranceProvider, InsuranceClaim
from app.extensions import db

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
    
    # ==================== Invoices ====================
    
    @staticmethod
    def create_invoice(data):
        """Create a new invoice with items"""
        invoice = Invoice(
            patient_id=data['patient_id'],
            invoice_number=BillingService.generate_invoice_number(),
            tax=data.get('tax', 0),
            discount=data.get('discount', 0),
            notes=data.get('notes'),
            due_date=data.get('due_date'),
            invoice_date=data.get('invoice_date', datetime.utcnow())
        )
        invoice.save()
        
        # Add invoice items
        for item_data in data.get('items', []):
            item = InvoiceItem(
                invoice_id=invoice.id,
                description=item_data['description'],
                quantity=item_data.get('quantity', 1),
                unit_price=item_data.get('unit_price', 0)
            )
            item.calculate_total()
            item.save()
        
        # Calculate totals
        invoice.calculate_total()
        invoice.save()
        
        return invoice
    
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
    def create_payment(invoice_id, data):
        """Create a payment for an invoice"""
        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            return None, "Invoice not found"
        
        payment = Payment(
            invoice_id=invoice_id,
            amount=data['amount'],
            payment_method=data['payment_method'],
            reference_number=data.get('reference_number'),
            notes=data.get('notes'),
            payment_date=data.get('payment_date', datetime.utcnow())
        )
        payment.save()
        
        # Update invoice status
        total_paid = sum(p.amount for p in invoice.payments)
        
        if total_paid >= invoice.total:
            invoice.status = 'PAID'
            invoice.paid_date = datetime.utcnow()
        else:
            invoice.status = 'PARTIAL'
        
        invoice.save()
        
        return payment, None
    
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
