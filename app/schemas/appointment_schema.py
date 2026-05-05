from marshmallow import Schema, fields, validate

class AppointmentSchema(Schema):
    id = fields.String(dump_only=True)
    patient_id = fields.String(required=True)
    doctor_id = fields.String(required=True)
    appointment_date = fields.DateTime(required=True)
    status = fields.String(validate=validate.OneOf(['SCHEDULED', 'COMPLETED', 'CANCELLED', 'NO_SHOW']))
    reason = fields.String()
    notes = fields.String()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
