from flask_restx import Namespace, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.resources.base_resource import BaseResource
from app.services.medical_record_service import MedicalRecordService
from app.schemas.medical_record_schema import MedicalRecordSchema, ClinicalNoteSchema
from app.utils.decorators import role_required

emr_ns = Namespace('emr', description='Electronic Medical Records operations')

# Swagger models
medical_record_model = emr_ns.model('MedicalRecord', {
    'patient_id': fields.String(required=True),
    'appointment_id': fields.String(),
    'chief_complaint': fields.String(),
    'vital_signs': fields.Raw(),
    'symptoms': fields.List(fields.String()),
    'diagnosis': fields.List(fields.String()),
    'treatment_plan': fields.String(),
    'prescriptions': fields.List(fields.Raw()),
    'lab_orders': fields.List(fields.Raw()),
    'follow_up_date': fields.String(),
    'notes': fields.String()
})

clinical_note_model = emr_ns.model('ClinicalNote', {
    'patient_id': fields.String(required=True),
    'record_id': fields.String(),
    'note_type': fields.String(),
    'title': fields.String(),
    'content': fields.String(required=True),
    'is_confidential': fields.Boolean()
})


# ==================== Medical Records ====================

class MedicalRecordListResource(BaseResource):
    """Resource for listing and creating medical records"""
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE')
    def get(self):
        """Get medical records for a patient"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        patient_id = request.args.get('patient_id')
        
        if not patient_id:
            return self.handle_error("Please provide patient_id", 400)
        
        # Verify patient belongs to user's facility
        from app.models.patient import Patient
        patient = Patient.query.filter_by(id=patient_id, facility_slug=facility_slug).first()
        if not patient:
            return self.handle_error("Patient not found", 404)
        
        records = MedicalRecordService.get_medical_records_by_patient(patient_id, facility_slug)
        schema = MedicalRecordSchema(many=True)
        return self.handle_response(data=schema.dump(records))
    
    @role_required('ADMIN', 'DOCTOR')
    @emr_ns.expect(medical_record_model)
    def post(self):
        """Create a new medical record"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        schema = MedicalRecordSchema()
        data = schema.load(emr_ns.payload)
        
        # Force facility_slug
        data['facility_slug'] = facility_slug
        
        current_user_id = get_jwt_identity()
        record = MedicalRecordService.create_medical_record(data, current_user_id)
        
        return self.handle_response(
            data=schema.dump(record),
            message="Medical record created successfully",
            status_code=201
        )


class MedicalRecordResource(BaseResource):
    """Resource for individual medical record operations"""
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE')
    def get(self, record_id):
        """Get medical record by ID"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        record = MedicalRecordService.get_medical_record_by_id(record_id)
        
        if not record:
            return self.handle_error("Medical record not found", 404)
        
        # Verify record belongs to user's facility
        if record.facility_slug != facility_slug:
            return self.handle_error("Medical record not found", 404)
        
        schema = MedicalRecordSchema()
        return self.handle_response(data=schema.dump(record))
    
    @role_required('ADMIN', 'DOCTOR')
    @emr_ns.expect(medical_record_model)
    def put(self, record_id):
        """Update medical record"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        record = MedicalRecordService.get_medical_record_by_id(record_id)
        
        if not record:
            return self.handle_error("Medical record not found", 404)
        
        # Verify record belongs to user's facility
        if record.facility_slug != facility_slug:
            return self.handle_error("Medical record not found", 404)
        
        schema = MedicalRecordSchema(partial=True)
        data = schema.load(emr_ns.payload)
        
        updated_record = MedicalRecordService.update_medical_record(record, data)
        
        return self.handle_response(
            data=schema.dump(updated_record),
            message="Medical record updated successfully"
        )


# ==================== Clinical Notes ====================

class ClinicalNoteListResource(BaseResource):
    """Resource for listing and creating clinical notes"""
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE')
    def get(self):
        """Get clinical notes for a patient"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        patient_id = request.args.get('patient_id')
        
        if not patient_id:
            return self.handle_error("Please provide patient_id", 400)
        
        # Verify patient belongs to user's facility
        from app.models.patient import Patient
        patient = Patient.query.filter_by(id=patient_id, facility_slug=facility_slug).first()
        if not patient:
            return self.handle_error("Patient not found", 404)
        
        notes = MedicalRecordService.get_clinical_notes_by_patient(patient_id, facility_slug)
        schema = ClinicalNoteSchema(many=True)
        return self.handle_response(data=schema.dump(notes))
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE')
    @emr_ns.expect(clinical_note_model)
    def post(self):
        """Create a new clinical note"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        schema = ClinicalNoteSchema()
        data = schema.load(emr_ns.payload)
        
        # Force facility_slug
        data['facility_slug'] = facility_slug
        
        current_user_id = get_jwt_identity()
        note = MedicalRecordService.create_clinical_note(data, current_user_id)
        
        return self.handle_response(
            data=schema.dump(note),
            message="Clinical note created successfully",
            status_code=201
        )


class ClinicalNoteResource(BaseResource):
    """Resource for individual clinical note operations"""
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE')
    def get(self, note_id):
        """Get clinical note by ID"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        note = MedicalRecordService.get_clinical_note_by_id(note_id)
        
        if not note:
            return self.handle_error("Clinical note not found", 404)
        
        # Verify note belongs to user's facility
        if note.facility_slug != facility_slug:
            return self.handle_error("Clinical note not found", 404)
        
        schema = ClinicalNoteSchema()
        return self.handle_response(data=schema.dump(note))
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE')
    @emr_ns.expect(clinical_note_model)
    def put(self, note_id):
        """Update clinical note"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        note = MedicalRecordService.get_clinical_note_by_id(note_id)
        
        if not note:
            return self.handle_error("Clinical note not found", 404)
        
        # Verify note belongs to user's facility
        if note.facility_slug != facility_slug:
            return self.handle_error("Clinical note not found", 404)
        
        schema = ClinicalNoteSchema(partial=True)
        data = schema.load(emr_ns.payload)
        
        updated_note = MedicalRecordService.update_clinical_note(note, data)
        
        return self.handle_response(
            data=schema.dump(updated_note),
            message="Clinical note updated successfully"
        )


# Register resources
emr_ns.add_resource(MedicalRecordListResource, '/records')
emr_ns.add_resource(MedicalRecordResource, '/records/<string:record_id>')
emr_ns.add_resource(ClinicalNoteListResource, '/notes')
emr_ns.add_resource(ClinicalNoteResource, '/notes/<string:note_id>')
