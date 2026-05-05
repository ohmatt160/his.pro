from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.resources.base_resource import BaseResource
from app.models.radiology import Radiology
from app.models.patient import Patient
from app.models.user import User
from app.utils.decorators import role_required
from app.utils.validators import Validators
from app.extensions import db
from datetime import datetime

radiology_ns = Namespace('radiology', description='Radiology order management operations')

# Swagger models
radiology_model = radiology_ns.model('Radiology', {
    'patient_id': fields.String(required=True),
    'facility_slug': fields.String(required=True),
    'modality': fields.String(required=True),
    'body_part': fields.String(required=True),
    'clinical_notes': fields.String()
})

radiology_update_model = radiology_ns.model('RadiologyUpdate', {
    'status': fields.String(),
    'radiologist_id': fields.String(),
    'clinical_notes': fields.String()
})

radiology_report_model = radiology_ns.model('RadiologyReport', {
    'report': fields.String(required=True)
})


class RadiologyListResource(BaseResource):
    """Resource for listing and creating radiology orders"""
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE', 'RADIOLOGIST')
    def get(self):
        """Get paginated list of radiology orders"""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Filters
        facility_slug = request.args.get('facility_slug')
        status = request.args.get('status')
        patient_id = request.args.get('patient_id')
        
        if per_page > 100:
            per_page = 100
        
        # Get current user
        current_user = self.get_current_user()
        
        # Build query based on user role and facility
        query = Radiology.query
        
        # Filter by facility if not admin
        if current_user.role != 'ADMIN' and current_user.facility_slug:
            query = query.filter_by(facility_slug=current_user.facility_slug)
        elif facility_slug:
            query = query.filter_by(facility_slug=facility_slug)
        
        if status:
            query = query.filter_by(status=status)
        
        if patient_id:
            query = query.filter_by(patient_id=patient_id)
        
        # Order by request_date descending
        query = query.order_by(Radiology.request_date.desc())
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        orders = pagination.items
        
        # Build response with patient info
        result = []
        for order in orders:
            order_data = order.to_dict()
            if order.patient:
                order_data['patient_name'] = f"{order.patient.first_name} {order.patient.last_name}"
            if order.requester:
                order_data['requested_by_name'] = order.requester.full_name
            result.append(order_data)
        
        return self.handle_response(data={
            'radiology_orders': result,
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        })
    
    @role_required('ADMIN', 'DOCTOR')
    @radiology_ns.expect(radiology_model)
    def post(self):
        """Create a new radiology order"""
        data = request.get_json()
        
        # Validate required fields
        if not data.get('patient_id'):
            return self.handle_error("Patient ID is required", 400)
        if not data.get('facility_slug'):
            return self.handle_error("Facility slug is required", 400)
        if not data.get('modality'):
            return self.handle_error("Modality is required", 400)
        if not data.get('body_part'):
            return self.handle_error("Body part is required", 400)
        
        # Validate patient exists
        patient = Patient.query.get(data['patient_id'])
        if not patient:
            return self.handle_error("Patient not found", 404)
        
        # Validate modality
        if data['modality'] not in Radiology.MODALITIES:
            return self.handle_error(f"Invalid modality. Must be one of: {', '.join(Radiology.MODALITIES)}", 400)
        
        # Get current user
        current_user = self.get_current_user()
        
        # Create radiology order
        radiology = Radiology(
            patient_id=data['patient_id'],
            facility_slug=data['facility_slug'],
            modality=data['modality'],
            body_part=data['body_part'],
            clinical_notes=Validators.sanitize_string(data.get('clinical_notes', '')),
            requested_by=current_user.id,
            status='pending'
        )
        
        db.session.add(radiology)
        db.session.commit()
        
        return self.handle_response(
            data=radiology.to_dict(),
            message="Radiology order created successfully",
            status_code=201
        )


class RadiologyResource(BaseResource):
    """Resource for individual radiology order operations"""
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE', 'RADIOLOGIST')
    def get(self, order_id):
        """Get radiology order by ID"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        # Filter by facility
        radiology = Radiology.query.filter_by(id=order_id, facility_slug=facility_slug).first()
        
        if not radiology:
            return self.handle_error("Radiology order not found", 404)
        
        order_data = radiology.to_dict()
        if radiology.patient:
            order_data['patient_name'] = f"{radiology.patient.first_name} {radiology.patient.last_name}"
        if radiology.requester:
            order_data['requested_by_name'] = radiology.requester.full_name
        if radiology.radiologist:
            order_data['radiologist_name'] = radiology.radiologist.full_name
        
        return self.handle_response(data=order_data)
    
    @role_required('ADMIN', 'DOCTOR', 'RADIOLOGIST')
    @radiology_ns.expect(radiology_update_model)
    def put(self, order_id):
        """Update radiology order"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        # Filter by facility
        radiology = Radiology.query.filter_by(id=order_id, facility_slug=facility_slug).first()
        
        if not radiology:
            return self.handle_error("Radiology order not found", 404)
        
        data = request.get_json()
        
        # Update status
        if 'status' in data:
            if data['status'] not in Radiology.STATUSES:
                return self.handle_error(f"Invalid status. Must be one of: {', '.join(Radiology.STATUSES)}", 400)
            radiology.status = data['status']
        
        # Update radiologist
        if 'radiologist_id' in data:
            radiologist = User.query.get(data['radiologist_id'])
            if not radiologist:
                return self.handle_error("Radiologist not found", 404)
            radiology.radiologist_id = data['radiologist_id']
        
        # Update clinical notes
        if 'clinical_notes' in data:
            radiology.clinical_notes = Validators.sanitize_string(data['clinical_notes'])
        
        db.session.commit()
        
        return self.handle_response(
            data=radiology.to_dict(),
            message="Radiology order updated successfully"
        )


class RadiologyReportResource(BaseResource):
    """Resource for radiology report operations"""
    
    @role_required('ADMIN', 'DOCTOR', 'RADIOLOGIST')
    def get(self, order_id):
        """Get radiology report"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        # Filter by facility
        radiology = Radiology.query.filter_by(id=order_id, facility_slug=facility_slug).first()
        
        if not radiology:
            return self.handle_error("Radiology order not found", 404)
        
        if not radiology.report:
            return self.handle_error("Report not available", 404)
        
        return self.handle_response(data={
            'report': radiology.report,
            'report_date': radiology.report_date.isoformat() if radiology.report_date else None
        })
    
    @role_required('ADMIN', 'RADIOLOGIST')
    @radiology_ns.expect(radiology_report_model)
    def put(self, order_id):
        """Add or update radiology report"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        # Filter by facility
        radiology = Radiology.query.filter_by(id=order_id, facility_slug=facility_slug).first()
        
        if not radiology:
            return self.handle_error("Radiology order not found", 404)
        
        data = request.get_json()
        
        if not data.get('report'):
            return self.handle_error("Report text is required", 400)
        
        radiology.report = Validators.sanitize_string(data['report'])
        radiology.report_date = datetime.utcnow()
        
        # Update status to completed if not already
        if radiology.status == 'ordered':
            radiology.status = 'completed'
        
        db.session.commit()
        
        return self.handle_response(
            data=radiology.to_dict(),
            message="Report added successfully"
        )


# Register resources
radiology_ns.add_resource(RadiologyListResource, '')
radiology_ns.add_resource(RadiologyResource, '/<string:order_id>')
radiology_ns.add_resource(RadiologyReportResource, '/<string:order_id>/report')