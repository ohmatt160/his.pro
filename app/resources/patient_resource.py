from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.resources.base_resource import BaseResource
from app.services.patient_service import PatientService
from app.schemas.patient_schema import PatientSchema
from app.utils.decorators import role_required
from app.utils.validators import Validators

patient_ns = Namespace('patients', description='Patient management operations')

# Swagger model
patient_model = patient_ns.model('Patient', {
    'first_name': fields.String(required=True),
    'last_name': fields.String(required=True),
    'date_of_birth': fields.String(required=True),
    'gender': fields.String(),
    'phone': fields.String(),
    'email': fields.String(),
    'address': fields.String(),
    'blood_type': fields.String(),
    'medical_history': fields.Raw(),
    'emergency_contact_name': fields.String(),
    'emergency_contact_phone': fields.String()
})

class PatientListResource(BaseResource):
    """Resource for listing and creating patients"""
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')
    def get(self):
        """Get paginated list of patients"""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', None)
        
        # Cap per_page at maximum 100
        if per_page > 100:
            per_page = 100
        
        # Get current user's facility for filtering (multi-tenant)
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        # Verify facility exists and is active
        if facility_slug:
            from app.models.facility import Facility
            facility = Facility.query.filter_by(slug=facility_slug, is_active=True).first()
            if not facility:
                return self.handle_error("Your facility is inactive or not found", 403)
        
        result = PatientService.get_all_patients(
            facility_slug=facility_slug,
            page=page, 
            per_page=per_page, 
            search=search
        )
        
        schema = PatientSchema(many=True)
        return self.handle_response(data={
            'patients': schema.dump(result['items']),
            'total': result['total'],
            'page': result['page'],
            'per_page': result['per_page'],
            'pages': result['pages']
        })
    
    @role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST')
    @patient_ns.expect(patient_model)
    def post(self):
        """Create a new patient"""
        schema = PatientSchema()
        data = schema.load(patient_ns.payload)
        
        # Sanitize string fields
        if 'first_name' in data:
            data['first_name'] = Validators.sanitize_string(data['first_name'])
        if 'last_name' in data:
            data['last_name'] = Validators.sanitize_string(data['last_name'])
        if 'phone' in data:
            data['phone'] = Validators.sanitize_string(data.get('phone', ''))
        if 'email' in data:
            data['email'] = Validators.sanitize_string(data.get('email', ''))
        if 'address' in data:
            data['address'] = Validators.sanitize_string(data.get('address', ''))
        if 'emergency_contact_name' in data:
            data['emergency_contact_name'] = Validators.sanitize_string(data.get('emergency_contact_name', ''))
        if 'emergency_contact_phone' in data:
            data['emergency_contact_phone'] = Validators.sanitize_string(data.get('emergency_contact_phone', ''))
        
        current_user_id = get_jwt_identity()
        current_user = self.get_current_user()
        patient = PatientService.create_patient(data, current_user_id, current_user.facility_slug if current_user else None)
        
        return self.handle_response(
            data=schema.dump(patient),
            message="Patient created successfully",
            status_code=201
        )

class PatientResource(BaseResource):
    """Resource for individual patient operations"""
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')
    def get(self, patient_id):
        """Get patient by ID"""
        # Get current user's facility for filtering (multi-tenant)
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        # Filter by facility
        patient = PatientService.get_patient_by_id(patient_id, facility_slug)
        
        if not patient:
            return self.handle_error("Patient not found", 404)
        
        schema = PatientSchema()
        return self.handle_response(data=schema.dump(patient))
    
    @role_required('ADMIN', 'DOCTOR')
    @patient_ns.expect(patient_model)
    def put(self, patient_id):
        """Update patient"""
        # Get current user's facility for filtering (multi-tenant)
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        # Filter by facility
        patient = PatientService.get_patient_by_id(patient_id, facility_slug)
        
        if not patient:
            return self.handle_error("Patient not found", 404)
        
        schema = PatientSchema(partial=True)
        data = schema.load(patient_ns.payload)
        
        updated_patient = PatientService.update_patient(patient, data)
        
        return self.handle_response(
            data=schema.dump(updated_patient),
            message="Patient updated successfully"
        )
    
    @role_required('ADMIN')
    def delete(self, patient_id):
        """Delete patient (soft delete)"""
        # Get current user's facility for filtering (multi-tenant)
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        # Filter by facility
        patient = PatientService.get_patient_by_id(patient_id, facility_slug)
        
        if not patient:
            return self.handle_error("Patient not found", 404)
        
        PatientService.delete_patient(patient)
        
        return self.handle_response(message="Patient deleted successfully")

# Register resources
patient_ns.add_resource(PatientListResource, '')
patient_ns.add_resource(PatientResource, '/<string:patient_id>')
