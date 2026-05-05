from flask_restx import Namespace, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.resources.base_resource import BaseResource
from app.services.appointment_service import AppointmentService
from app.schemas.appointment_schema import AppointmentSchema
from app.utils.decorators import role_required
from app.utils.validators import Validators

appointment_ns = Namespace('appointments', description='Appointment management')

# Swagger model
appointment_model = appointment_ns.model('Appointment', {
    'patient_id': fields.String(required=True),
    'doctor_id': fields.String(required=True),
    'appointment_date': fields.String(required=True),
    'reason': fields.String(),
    'notes': fields.String()
})

class AppointmentListResource(BaseResource):
    """Resource for listing and creating appointments"""
    
    @role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST')
    def get(self):
        """Get appointments for user's facility"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        patient_id = request.args.get('patient_id')
        doctor_id = request.args.get('doctor_id')
        
        schema = AppointmentSchema(many=True)
        
        if patient_id:
            # Also filter by facility
            appointments = AppointmentService.get_appointments_by_patient(patient_id, facility_slug)
            return self.handle_response(data=schema.dump(appointments))
        elif doctor_id:
            # Also filter by facility
            appointments = AppointmentService.get_appointments_by_doctor(doctor_id, facility_slug)
            return self.handle_response(data=schema.dump(appointments))
        else:
            # Get all appointments for facility
            from app.models.appointment import Appointment
            appointments = Appointment.query.filter_by(facility_slug=facility_slug).order_by(Appointment.scheduled_time.desc()).all()
            return self.handle_response(data=schema.dump(appointments))
    
    @role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST')
    @appointment_ns.expect(appointment_model)
    def post(self):
        """Create a new appointment"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        schema = AppointmentSchema()
        data = schema.load(appointment_ns.payload)
        
        # Force facility_slug
        data['facility_slug'] = facility_slug
        
        # Sanitize string fields
        if 'reason' in data:
            data['reason'] = Validators.sanitize_string(data.get('reason', ''))
        if 'notes' in data:
            data['notes'] = Validators.sanitize_string(data.get('notes', ''))
        
        appointment = AppointmentService.create_appointment(data)
        
        return self.handle_response(
            data=schema.dump(appointment),
            message="Appointment created successfully",
            status_code=201
        )

class AppointmentResource(BaseResource):
    """Resource for individual appointment operations"""
    
    @role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST')
    def get(self, appointment_id):
        """Get appointment by ID"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        appointment = AppointmentService.get_appointment_by_id(appointment_id)
        
        if not appointment:
            return self.handle_error("Appointment not found", 404)
        
        # Verify appointment belongs to user's facility
        if appointment.facility_slug != facility_slug:
            return self.handle_error("Appointment not found", 404)
        
        schema = AppointmentSchema()
        return self.handle_response(data=schema.dump(appointment))
    
    @role_required('ADMIN', 'DOCTOR')
    def put(self, appointment_id):
        """Update appointment status"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        appointment = AppointmentService.get_appointment_by_id(appointment_id)
        
        if not appointment:
            return self.handle_error("Appointment not found", 404)
        
        # Verify appointment belongs to user's facility
        if appointment.facility_slug != facility_slug:
            return self.handle_error("Appointment not found", 404)
        
        status = request.json.get('status')
        
        if status:
            updated_appointment = AppointmentService.update_appointment_status(appointment, status)
            schema = AppointmentSchema()
            return self.handle_response(
                data=schema.dump(updated_appointment),
                message="Appointment updated successfully"
            )
        
        return self.handle_error("Status is required", 400)
    
    @role_required('ADMIN', 'DOCTOR')
    def delete(self, appointment_id):
        """Cancel appointment"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        appointment = AppointmentService.get_appointment_by_id(appointment_id)
        
        if not appointment:
            return self.handle_error("Appointment not found", 404)
        
        # Verify appointment belongs to user's facility
        if appointment.facility_slug != facility_slug:
            return self.handle_error("Appointment not found", 404)
        
        cancelled_appointment = AppointmentService.cancel_appointment(appointment)
        schema = AppointmentSchema()
        
        return self.handle_response(
            data=schema.dump(cancelled_appointment),
            message="Appointment cancelled successfully"
        )

# Register resources
appointment_ns.add_resource(AppointmentListResource, '')
appointment_ns.add_resource(AppointmentResource, '/<string:appointment_id>')
