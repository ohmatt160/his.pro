from marshmallow import Schema, fields, validate

class MedicalRecordSchema(Schema):
    id = fields.String(dump_only=True)
    patient_id = fields.String(required=True)
    appointment_id = fields.String()
    created_by = fields.String(dump_only=True)
    chief_complaint = fields.String()
    vital_signs = fields.Dict()
    symptoms = fields.List(fields.String())
    diagnosis = fields.List(fields.String())
    treatment_plan = fields.String()
    prescriptions = fields.List(fields.Dict())
    lab_orders = fields.List(fields.Dict())
    follow_up_date = fields.Date()
    notes = fields.String()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class ClinicalNoteSchema(Schema):
    id = fields.String(dump_only=True)
    patient_id = fields.String(required=True)
    record_id = fields.String()
    created_by = fields.String(dump_only=True)
    note_type = fields.String(validate=validate.OneOf(['PROGRESS', 'INITIAL', 'DISCHARGE', 'REFERRAL']))
    title = fields.String(validate=validate.Length(max=200))
    content = fields.String(required=True)
    is_confidential = fields.Boolean()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
