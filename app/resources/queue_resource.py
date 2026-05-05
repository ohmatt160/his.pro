from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.resources.base_resource import BaseResource
from app.models.patient_queue import PatientQueue
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.utils.decorators import role_required
from app.utils.validators import Validators
from app.extensions import db
from datetime import datetime

queue_ns = Namespace('queue', description='Patient queue management operations')

# Swagger models
queue_model = queue_ns.model('Queue', {
    'patient_id': fields.String(required=True),
    'facility_slug': fields.String(required=True),
    'appointment_id': fields.String(),
    'department': fields.String(required=True),
    'priority': fields.String()
})

queue_update_model = queue_ns.model('QueueUpdate', {
    'status': fields.String(),
    'priority': fields.String(),
    'department': fields.String()
})


class QueueListResource(BaseResource):
    """Resource for listing and creating queue entries"""
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')
    def get(self):
        """Get queue for user's facility"""
        # Get current user's facility - ALWAYS use user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Filters - only status and department allowed
        status = request.args.get('status')
        department = request.args.get('department')
        
        if per_page > 100:
            per_page = 100
        
        # Build query - ALWAYS filter by user's facility
        query = PatientQueue.query.filter_by(facility_slug=facility_slug)
        
        if status:
            query = query.filter_by(status=status)
        
        if department:
            query = query.filter_by(department=department)
        
        # Order by priority and queue_number
        query = query.order_by(
            db.case(
                (PatientQueue.priority == 'urgent', 1),
                else_=2
            ),
            PatientQueue.queue_number
        )
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        entries = pagination.items
        
        # Build response with patient and appointment info
        result = []
        for entry in entries:
            entry_data = entry.to_dict()
            if entry.patient:
                entry_data['patient_name'] = f"{entry.patient.first_name} {entry.patient.last_name}"
                entry_data['patient_phone'] = entry.patient.phone
            if entry.appointment:
                entry_data['appointment_time'] = entry.appointment.scheduled_time.isoformat() if entry.appointment.scheduled_time else None
            result.append(entry_data)
        
        return self.handle_response(data={
            'queue_entries': result,
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        })
    
    @role_required('ADMIN', 'RECEPTIONIST')
    @queue_ns.expect(queue_model)
    def post(self):
        """Add patient to queue"""
        # Get current user's facility - ALWAYS use user's facility
        current_user = self.get_current_user()
        user_facility = current_user.facility_slug if current_user else None
        
        if not user_facility:
            return self.handle_error("User is not associated with a facility", 400)
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('patient_id'):
            return self.handle_error("Patient ID is required", 400)
        if not data.get('department'):
            return self.handle_error("Department is required", 400)
        
        # Validate patient exists AND belongs to user's facility
        patient = Patient.query.filter_by(id=data['patient_id'], facility_slug=user_facility).first()
        if not patient:
            return self.handle_error("Patient not found", 404)
        
        # Validate appointment if provided - must belong to user's facility
        if data.get('appointment_id'):
            appointment = Appointment.query.filter_by(id=data['appointment_id'], facility_slug=user_facility).first()
            if not appointment:
                return self.handle_error("Appointment not found", 404)
        
        # ALWAYS use user's facility
        facility_slug = user_facility
        
        # Check if patient is already in queue for this facility
        existing = PatientQueue.query.filter(
            PatientQueue.patient_id == data['patient_id'],
            PatientQueue.facility_slug == facility_slug,
            PatientQueue.status.in_(['waiting', 'in_progress'])
        ).first()
        if existing:
            return self.handle_error("Patient is already in queue", 400)
        
        # Get next queue number for the facility and department
        last_entry = PatientQueue.query.filter_by(
            facility_slug=facility_slug,
            department=data['department']
        ).order_by(PatientQueue.queue_number.desc()).first()
        
        next_number = (last_entry.queue_number + 1) if last_entry else 1
        
        # Create queue entry
        queue_entry = PatientQueue(
            facility_slug=facility_slug,
            patient_id=data['patient_id'],
            appointment_id=data.get('appointment_id'),
            department=data['department'],
            priority=data.get('priority', 'normal'),
            queue_number=next_number,
            status='waiting'
        )
        
        db.session.add(queue_entry)
        db.session.commit()
        
        return self.handle_response(
            data=queue_entry.to_dict(),
            message="Patient added to queue successfully",
            status_code=201
        )


class QueueResource(BaseResource):
    """Resource for individual queue entry operations"""
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')
    def get(self, queue_id):
        """Get queue entry by ID"""
        # Get current user's facility - ALWAYS use user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        queue_entry = PatientQueue.query.filter_by(id=queue_id, facility_slug=facility_slug).first()
        
        if not queue_entry:
            return self.handle_error("Queue entry not found", 404)
        
        entry_data = queue_entry.to_dict()
        if queue_entry.patient:
            entry_data['patient_name'] = f"{queue_entry.patient.first_name} {queue_entry.patient.last_name}"
            entry_data['patient_phone'] = queue_entry.patient.phone
            entry_data['patient_date_of_birth'] = queue_entry.patient.date_of_birth.isoformat() if queue_entry.patient.date_of_birth else None
        if queue_entry.appointment:
            entry_data['appointment_time'] = queue_entry.appointment.scheduled_time.isoformat() if queue_entry.appointment.scheduled_time else None
        
        return self.handle_response(data=entry_data)
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE')
    @queue_ns.expect(queue_update_model)
    def put(self, queue_id):
        """Update queue entry"""
        # Get current user's facility - ALWAYS use user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        queue_entry = PatientQueue.query.filter_by(id=queue_id, facility_slug=facility_slug).first()
        
        if not queue_entry:
            return self.handle_error("Queue entry not found", 404)
        
        data = request.get_json()
        
        # Update status
        if 'status' in data:
            if data['status'] not in PatientQueue.STATUSES:
                return self.handle_error(f"Invalid status. Must be one of: {', '.join(PatientQueue.STATUSES)}", 400)
            queue_entry.status = data['status']
        
        # Update priority
        if 'priority' in data:
            if data['priority'] not in PatientQueue.PRIORITIES:
                return self.handle_error(f"Invalid priority. Must be one of: {', '.join(PatientQueue.PRIORITIES)}", 400)
            queue_entry.priority = data['priority']
        
        # Update department
        if 'department' in data and data['department']:
            queue_entry.department = Validators.sanitize_string(data['department'])
        
        db.session.commit()
        
        return self.handle_response(
            data=queue_entry.to_dict(),
            message="Queue entry updated successfully"
        )
    
    @role_required('ADMIN', 'RECEPTIONIST')
    def delete(self, queue_id):
        """Remove patient from queue"""
        # Get current user's facility - ALWAYS use user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        queue_entry = PatientQueue.query.filter_by(id=queue_id, facility_slug=facility_slug).first()
        
        if not queue_entry:
            return self.handle_error("Queue entry not found", 404)
        
        if queue_entry.status == 'in_progress':
            return self.handle_error("Cannot remove patient whose visit is in progress", 400)
        
        db.session.delete(queue_entry)
        db.session.commit()
        
        return self.handle_response(message="Patient removed from queue successfully")


class QueueCheckinResource(BaseResource):
    """Resource for patient check-in"""
    
    @role_required('ADMIN', 'RECEPTIONIST')
    def put(self, queue_id):
        """Check in patient"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        # Filter by facility
        queue_entry = PatientQueue.query.filter_by(id=queue_id, facility_slug=facility_slug).first()
        
        if not queue_entry:
            return self.handle_error("Queue entry not found", 404)
        
        if queue_entry.status not in ['waiting']:
            return self.handle_error("Patient cannot be checked in", 400)
        
        queue_entry.check_in()
        db.session.commit()
        
        return self.handle_response(
            data=queue_entry.to_dict(),
            message="Patient checked in successfully"
        )


class QueueStartResource(BaseResource):
    """Resource for starting patient visit"""
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE')
    def put(self, queue_id):
        """Start patient visit"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        # Filter by facility
        queue_entry = PatientQueue.query.filter_by(id=queue_id, facility_slug=facility_slug).first()
        
        if not queue_entry:
            return self.handle_error("Queue entry not found", 404)
        
        if queue_entry.status != 'waiting':
            return self.handle_error("Patient is not in waiting status", 400)
        
        queue_entry.start_visit()
        db.session.commit()
        
        return self.handle_response(
            data=queue_entry.to_dict(),
            message="Visit started successfully"
        )


class QueueCompleteResource(BaseResource):
    """Resource for completing patient visit"""
    
    @role_required('ADMIN', 'DOCTOR')
    def put(self, queue_id):
        """Complete patient visit"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        # Filter by facility
        queue_entry = PatientQueue.query.filter_by(id=queue_id, facility_slug=facility_slug).first()
        
        if not queue_entry:
            return self.handle_error("Queue entry not found", 404)
        
        if queue_entry.status != 'in_progress':
            return self.handle_error("Patient visit is not in progress", 400)
        
        queue_entry.complete_visit()
        db.session.commit()
        
        return self.handle_response(
            data=queue_entry.to_dict(),
            message="Visit completed successfully"
        )


# Register resources
queue_ns.add_resource(QueueListResource, '')
queue_ns.add_resource(QueueResource, '/<string:queue_id>')
queue_ns.add_resource(QueueCheckinResource, '/<string:queue_id>/checkin')
queue_ns.add_resource(QueueStartResource, '/<string:queue_id>/start')
queue_ns.add_resource(QueueCompleteResource, '/<string:queue_id>/complete')