from marshmallow import Schema, fields, validate
from datetime import datetime

class InvoiceItemSchema(Schema):
    id = fields.String(dump_only=True)
    description = fields.String(required=True, validate=validate.Length(max=500))
    quantity = fields.Integer(required=True)
    unit_price = fields.Decimal(places=2)
    total = fields.Decimal(places=2, dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class InvoiceSchema(Schema):
    id = fields.String(dump_only=True)
    patient_id = fields.String(required=True)
    invoice_number = fields.String(dump_only=True)
    status = fields.String(validate=validate.OneOf(['PENDING', 'PAID', 'PARTIAL', 'CANCELLED']))
    subtotal = fields.Decimal(places=2, dump_only=True)
    tax = fields.Decimal(places=2)
    discount = fields.Decimal(places=2)
    total = fields.Decimal(places=2, dump_only=True)
    notes = fields.String()
    due_date = fields.Date()
    invoice_date = fields.DateTime(required=True)
    paid_date = fields.DateTime(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class InvoiceWithItemsSchema(Schema):
    """Schema for creating invoice with items"""
    patient_id = fields.String(required=True)
    items = fields.List(fields.Nested(InvoiceItemSchema), required=True)
    tax = fields.Decimal(places=2)
    discount = fields.Decimal(places=2)
    notes = fields.String()
    due_date = fields.Date()


class PaymentSchema(Schema):
    id = fields.String(dump_only=True)
    invoice_id = fields.String(required=True)
    amount = fields.Decimal(places=2, required=True)
    payment_method = fields.String(required=True, validate=validate.OneOf(['CASH', 'CARD', 'TRANSFER', 'INSURANCE']))
    reference_number = fields.String(validate=validate.Length(max=100))
    notes = fields.String()
    payment_date = fields.DateTime(required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class InsuranceProviderSchema(Schema):
    id = fields.String(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(max=200))
    code = fields.String(required=True, validate=validate.Length(max=50))
    contact_number = fields.String(validate=validate.Length(max=20))
    email = fields.Email()
    address = fields.String()
    is_active = fields.Boolean()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class InsuranceClaimSchema(Schema):
    id = fields.String(dump_only=True)
    invoice_id = fields.String(required=True)
    insurance_provider_id = fields.String()
    policy_number = fields.String(validate=validate.Length(max=100))
    claim_number = fields.String(dump_only=True)
    claimed_amount = fields.Decimal(places=2)
    approved_amount = fields.Decimal(places=2)
    status = fields.String(validate=validate.OneOf(['PENDING', 'SUBMITTED', 'APPROVED', 'REJECTED']))
    claim_date = fields.DateTime(dump_only=True)
    settlement_date = fields.DateTime(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
