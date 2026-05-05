from marshmallow import Schema, fields, validate

class MedicationSchema(Schema):
    id = fields.String(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=1, max=200))
    code = fields.String(required=True, validate=validate.Length(min=1, max=50))
    generic_name = fields.String(validate=validate.Length(max=200))
    description = fields.String()
    category = fields.String(validate=validate.Length(max=100))
    unit = fields.String(validate=validate.Length(max=50))
    strength = fields.String(validate=validate.Length(max=50))
    price = fields.Decimal(places=2)
    reorder_level = fields.Integer()
    is_active = fields.Boolean()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class PharmacyInventorySchema(Schema):
    id = fields.String(dump_only=True)
    medication_id = fields.String(required=True)
    quantity = fields.Integer(required=True)
    expiry_date = fields.Date()
    batch_number = fields.String(validate=validate.Length(max=100))
    location = fields.String(validate=validate.Length(max=50))
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class PrescriptionItemSchema(Schema):
    id = fields.String(dump_only=True)
    medication_id = fields.String(required=True)
    quantity = fields.Integer(required=True)
    dosage = fields.String(validate=validate.Length(max=100))
    instructions = fields.String()
    is_dispensed = fields.Boolean()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class PrescriptionSchema(Schema):
    id = fields.String(dump_only=True)
    patient_id = fields.String(required=True)
    prescribed_by = fields.String(dump_only=True)
    status = fields.String(validate=validate.OneOf(['PENDING', 'DISPENSED', 'CANCELLED']))
    notes = fields.String()
    prescription_date = fields.DateTime(required=True)
    dispensed_by = fields.String(dump_only=True)
    dispensed_date = fields.DateTime(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class PrescriptionWithItemsSchema(Schema):
    """Schema for creating prescription with items"""
    patient_id = fields.String(required=True)
    items = fields.List(fields.Nested(PrescriptionItemSchema), required=True)
    notes = fields.String()
