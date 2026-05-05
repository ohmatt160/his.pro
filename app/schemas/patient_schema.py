from marshmallow import Schema, fields, validate
from datetime import date

class PatientSchema(Schema):
    id = fields.String(dump_only=True)
    first_name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    last_name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    date_of_birth = fields.Date(required=True)
    gender = fields.String(validate=validate.OneOf(['MALE', 'FEMALE', 'OTHER']))
    phone = fields.String()
    email = fields.Email()
    address = fields.String()
    blood_type = fields.String(validate=validate.OneOf(['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']))
    medical_history = fields.Dict()
    emergency_contact_name = fields.String()
    emergency_contact_phone = fields.String()
    created_by = fields.String(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    full_name = fields.String(dump_only=True)
