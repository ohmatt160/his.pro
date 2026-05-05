from flask_restx import Namespace, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.resources.base_resource import BaseResource
from app.services.billing_service import BillingService
from app.schemas.billing_schema import InvoiceSchema, InvoiceItemSchema, PaymentSchema, InsuranceProviderSchema, InsuranceClaimSchema
from app.utils.decorators import role_required
from app.utils.validators import Validators

billing_ns = Namespace('billing', description='Billing and invoicing operations')

# Swagger models
invoice_item_model = billing_ns.model('InvoiceItem', {
    'description': fields.String(required=True),
    'quantity': fields.Integer(required=True),
    'unit_price': fields.Float(required=True)
})

invoice_model = billing_ns.model('Invoice', {
    'patient_id': fields.String(required=True),
    'items': fields.List(fields.Nested(invoice_item_model), required=True),
    'tax': fields.Float(),
    'discount': fields.Float(),
    'notes': fields.String(),
    'due_date': fields.String()
})

payment_model = billing_ns.model('Payment', {
    'amount': fields.Float(required=True),
    'payment_method': fields.String(required=True),
    'reference_number': fields.String(),
    'notes': fields.String()
})

insurance_provider_model = billing_ns.model('InsuranceProvider', {
    'name': fields.String(required=True),
    'code': fields.String(required=True),
    'contact_number': fields.String(),
    'email': fields.String(),
    'address': fields.String()
})

insurance_claim_model = billing_ns.model('InsuranceClaim', {
    'invoice_id': fields.String(required=True),
    'insurance_provider_id': fields.String(),
    'policy_number': fields.String(),
    'claimed_amount': fields.Float()
})


# ==================== Invoices ====================

class InvoiceListResource(BaseResource):
    """Resource for listing and creating invoices"""
    
    @role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST')
    def get(self):
        """Get invoices for user's facility"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        patient_id = request.args.get('patient_id')
        status = request.args.get('status')
        
        # Always filter by facility
        if patient_id:
            invoices = BillingService.get_invoices_by_patient(patient_id, facility_slug)
        elif status == 'PENDING':
            invoices = BillingService.get_pending_invoices(facility_slug)
        else:
            # Get all invoices for facility
            from app.models.billing import Invoice
            invoices = Invoice.query.filter_by(facility_slug=facility_slug).order_by(Invoice.created_at.desc()).all()
        
        schema = InvoiceSchema(many=True)
        return self.handle_response(data=schema.dump(invoices))
    
    @role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST')
    @billing_ns.expect(invoice_model)
    def post(self):
        """Create a new invoice"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        schema = InvoiceSchema()
        data = schema.load(billing_ns.payload)
        
        # Force facility_slug
        data['facility_slug'] = facility_slug
        
        # Sanitize string fields
        if 'notes' in data:
            data['notes'] = Validators.sanitize_string(data.get('notes', ''))
        
        invoice = BillingService.create_invoice(data)
        
        return self.handle_response(
            data=schema.dump(invoice),
            message="Invoice created successfully",
            status_code=201
        )


class InvoiceResource(BaseResource):
    """Resource for individual invoice operations"""
    
    @role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST')
    def get(self, invoice_id):
        """Get invoice by ID"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        invoice = BillingService.get_invoice_by_id(invoice_id)
        
        if not invoice:
            return self.handle_error("Invoice not found", 404)
        
        # Verify invoice belongs to user's facility
        if invoice.facility_slug != facility_slug:
            return self.handle_error("Invoice not found", 404)
        
        schema = InvoiceSchema()
        return self.handle_response(data=schema.dump(invoice))
    
    @role_required('ADMIN')
    @billing_ns.expect(invoice_model)
    def put(self, invoice_id):
        """Update invoice"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        invoice = BillingService.get_invoice_by_id(invoice_id)
        
        if not invoice:
            return self.handle_error("Invoice not found", 404)
        
        # Verify invoice belongs to user's facility
        if invoice.facility_slug != facility_slug:
            return self.handle_error("Invoice not found", 404)
        
        if invoice.status == 'PAID':
            return self.handle_error("Cannot update paid invoice", 400)
        
        schema = InvoiceSchema(partial=True)
        data = schema.load(billing_ns.payload)
        
        updated_invoice = BillingService.update_invoice(invoice, data)
        
        return self.handle_response(
            data=schema.dump(updated_invoice),
            message="Invoice updated successfully"
        )


# ==================== Payments ====================

class PaymentListResource(BaseResource):
    """Resource for listing and creating payments"""
    
    @role_required('ADMIN', 'RECEPTIONIST')
    def get(self):
        """Get payments for an invoice"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        invoice_id = request.args.get('invoice_id')
        
        if not invoice_id:
            return self.handle_error("Please provide invoice_id", 400)
        
        payments = BillingService.get_payments_by_invoice(invoice_id, facility_slug)
        schema = PaymentSchema(many=True)
        return self.handle_response(data=schema.dump(payments))
    
    @role_required('ADMIN', 'RECEPTIONIST')
    @billing_ns.expect(payment_model)
    def post(self):
        """Create a payment"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        invoice_id = billing_ns.payload.get('invoice_id')
        if not invoice_id:
            return self.handle_error("invoice_id is required", 400)
        
        schema = PaymentSchema()
        data = schema.load(billing_ns.payload)
        
        payment, error = BillingService.create_payment(invoice_id, data, facility_slug)
        
        if error:
            return self.handle_error(error, 400)
        
        return self.handle_response(
            data=schema.dump(payment),
            message="Payment recorded successfully",
            status_code=201
        )


# ==================== Insurance Providers ====================

class InsuranceProviderListResource(BaseResource):
    """Resource for insurance providers"""
    
    @role_required('ADMIN', 'RECEPTIONIST')
    def get(self):
        """Get all insurance providers for user's facility"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        providers = BillingService.get_all_insurance_providers(facility_slug=facility_slug, active_only=active_only)
        schema = InsuranceProviderSchema(many=True)
        return self.handle_response(data=schema.dump(providers))
    
    @role_required('ADMIN')
    @billing_ns.expect(insurance_provider_model)
    def post(self):
        """Create a new insurance provider"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        schema = InsuranceProviderSchema()
        data = schema.load(billing_ns.payload)
        
        # Force facility_slug
        data['facility_slug'] = facility_slug
        
        provider, error = BillingService.create_insurance_provider(data)
        
        if error:
            return self.handle_error(error, 400)
        
        return self.handle_response(
            data=schema.dump(provider),
            message="Insurance provider created successfully",
            status_code=201
        )


# ==================== Insurance Claims ====================

class InsuranceClaimListResource(BaseResource):
    """Resource for insurance claims"""
    
    @role_required('ADMIN', 'RECEPTIONIST')
    def get(self):
        """Get claims (filter by patient_id)"""
        patient_id = request.args.get('patient_id')
        
        if not patient_id:
            return self.handle_error("Please provide patient_id", 400)
        
        claims = BillingService.get_claims_by_patient(patient_id)
        schema = InsuranceClaimSchema(many=True)
        return self.handle_response(data=schema.dump(claims))
    
    @role_required('ADMIN', 'RECEPTIONIST')
    @billing_ns.expect(insurance_claim_model)
    def post(self):
        """Create a new insurance claim"""
        schema = InsuranceClaimSchema()
        data = schema.load(billing_ns.payload)
        
        claim, error = BillingService.create_insurance_claim(data)
        
        if error:
            return self.handle_error(error, 400)
        
        return self.handle_response(
            data=schema.dump(claim),
            message="Insurance claim created successfully",
            status_code=201
        )


class InsuranceClaimResource(BaseResource):
    """Resource for individual insurance claim operations"""
    
    @role_required('ADMIN', 'RECEPTIONIST')
    def put(self, claim_id):
        """Update insurance claim status"""
        status = request.json.get('status')
        approved_amount = request.json.get('approved_amount')
        
        if not status or status not in ['PENDING', 'SUBMITTED', 'APPROVED', 'REJECTED']:
            return self.handle_error("Valid status is required", 400)
        
        claim = BillingService.update_claim_status(claim_id, status, approved_amount)
        
        if not claim:
            return self.handle_error("Claim not found", 404)
        
        schema = InsuranceClaimSchema()
        return self.handle_response(
            data=schema.dump(claim),
            message="Insurance claim updated successfully"
        )


# Register resources
billing_ns.add_resource(InvoiceListResource, '/invoices')
billing_ns.add_resource(InvoiceResource, '/invoices/<string:invoice_id>')
billing_ns.add_resource(PaymentListResource, '/payments')
billing_ns.add_resource(InsuranceProviderListResource, '/insurance-providers')
billing_ns.add_resource(InsuranceClaimListResource, '/claims')
billing_ns.add_resource(InsuranceClaimResource, '/claims/<string:claim_id>')
