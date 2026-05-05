from marshmallow import Schema, fields, validate

class LabTestSchema(Schema):
    id = fields.String(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=1, max=200))
    code = fields.String(required=True, validate=validate.Length(min=1, max=50))
    description = fields.String()
    category = fields.String(validate=validate.Length(max=100))
    unit = fields.String(validate=validate.Length(max=50))
    reference_range = fields.String(validate=validate.Length(max=100))
    price = fields.Decimal(places=2)
    is_active = fields.Boolean()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class LabOrderSchema(Schema):
    id = fields.String(dump_only=True)
    patient_id = fields.String(required=True)
    test_id = fields.String(required=True)
    ordered_by = fields.String(dump_only=True)
    performed_by = fields.String()
    status = fields.String(validate=validate.OneOf(['PENDING', 'COLLECTED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']))
    priority = fields.String(validate=validate.OneOf(['ROUTINE', 'URGENT', 'EMERGENCY']))
    notes = fields.String()
    order_date = fields.DateTime(required=True)
    collection_date = fields.DateTime()
    completed_date = fields.DateTime(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class LabResultSchema(Schema):
    id = fields.String(dump_only=True)
    order_id = fields.String(required=True)
    value = fields.String()
    is_abnormal = fields.Boolean()
    notes = fields.String()
    result_date = fields.DateTime()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
