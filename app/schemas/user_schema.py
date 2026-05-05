from marshmallow import Schema, fields, validate

class UserSchema(Schema):
    id = fields.String(dump_only=True)
    username = fields.String(required=True, validate=validate.Length(min=3, max=80))
    email = fields.Email(required=True)
    facility_slug = fields.String()  # Include in output for frontend
    password = fields.String(load_only=True, required=True, validate=validate.Length(min=8))
    role = fields.String(required=True, validate=validate.OneOf(['ADMIN', 'DOCTOR', 'NURSE', 'LAB_TECH', 'PHARMACIST', 'RECEPTIONIST']))
    first_name = fields.String()
    last_name = fields.String()
    phone = fields.String()  # Add phone field for profile
    is_active = fields.Boolean(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class LoginSchema(Schema):
    username = fields.String(required=True)
    password = fields.String(required=True)
