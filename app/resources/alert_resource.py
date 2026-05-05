from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.resources.base_resource import BaseResource
from app.models.alert import Alert
from app.models.user import User
from app.utils.decorators import role_required
from app.utils.validators import Validators
from app.extensions import db
from datetime import datetime

alert_ns = Namespace('alerts', description='Alert management operations')

# Swagger models
alert_model = alert_ns.model('Alert', {
    'facility_slug': fields.String(required=True),
    'alert_type': fields.String(required=True),
    'title': fields.String(required=True),
    'message': fields.String(required=True),
    'recipient_id': fields.String(),
    'expires_at': fields.String()
})

alert_update_model = alert_ns.model('AlertUpdate', {
    'title': fields.String(),
    'message': fields.String(),
    'alert_type': fields.String()
})


class AlertListResource(BaseResource):
    """Resource for listing and creating alerts"""
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')
    def get(self):
        """Get paginated list of alerts"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Filters
        is_read = request.args.get('is_read')
        alert_type = request.args.get('alert_type')
        
        if per_page > 100:
            per_page = 100
        
        # Build query - ALWAYS filter by user's facility
        query = Alert.query.filter_by(facility_slug=facility_slug)
        
        # Filter by user (user can see their own alerts and facility-wide alerts)
        query = query.filter(
            db.or_(
                Alert.recipient_id == current_user.id,
                Alert.recipient_id == None
            )
        )
        
        # Filter by read status
        if is_read is not None:
            is_read_bool = is_read.lower() == 'true'
            query = query.filter_by(is_read=is_read_bool)
        
        # Filter by alert type
        if alert_type:
            query = query.filter_by(alert_type=alert_type)
        
        # Order by created_at descending
        query = query.order_by(Alert.created_at.desc())
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        alerts = pagination.items
        
        # Build response with recipient info
        result = []
        for alert in alerts:
            alert_data = alert.to_dict()
            if alert.recipient:
                alert_data['recipient_name'] = alert.recipient.full_name
            result.append(alert_data)
        
        return self.handle_response(data={
            'alerts': result,
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        })
    
    @role_required('ADMIN', 'DOCTOR')
    @alert_ns.expect(alert_model)
    def post(self):
        """Create a new alert"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        data = request.get_json()
        
        # Validate required fields (but use user's facility)
        if not data.get('alert_type'):
            return self.handle_error("Alert type is required", 400)
        if not data.get('title'):
            return self.handle_error("Title is required", 400)
        if not data.get('message'):
            return self.handle_error("Message is required", 400)
        
        # Validate alert type
        if data['alert_type'] not in Alert.ALERT_TYPES:
            return self.handle_error(f"Invalid alert_type. Must be one of: {', '.join(Alert.ALERT_TYPES)}", 400)
        
        # Validate recipient if provided - must belong to same facility
        if data.get('recipient_id'):
            recipient = User.query.get(data['recipient_id'])
            if not recipient:
                return self.handle_error("Recipient not found", 404)
            if recipient.facility_slug != facility_slug:
                return self.handle_error("Recipient not found", 404)
        
        # Create alert - ALWAYS use user's facility
        alert = Alert(
            facility_slug=facility_slug,
            alert_type=data['alert_type'],
            title=Validators.sanitize_string(data['title']),
            message=Validators.sanitize_string(data['message']),
            recipient_id=data.get('recipient_id')
        )
        
        # Parse expiry date if provided
        if data.get('expires_at'):
            try:
                alert.expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
            except ValueError:
                return self.handle_error("Invalid expires_at format. Use ISO 8601 format", 400)
        
        db.session.add(alert)
        db.session.commit()
        
        return self.handle_response(
            data=alert.to_dict(),
            message="Alert created successfully",
            status_code=201
        )


class AlertResource(BaseResource):
    """Resource for individual alert operations"""
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')
    def get(self, alert_id):
        """Get alert by ID"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        alert = Alert.query.filter_by(id=alert_id, facility_slug=facility_slug).first()
        
        if not alert:
            return self.handle_error("Alert not found", 404)
        
        alert_data = alert.to_dict()
        if alert.recipient:
            alert_data['recipient_name'] = alert.recipient.full_name
        
        return self.handle_response(data=alert_data)
    
    @role_required('ADMIN', 'DOCTOR')
    @alert_ns.expect(alert_update_model)
    def put(self, alert_id):
        """Update alert"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        alert = Alert.query.filter_by(id=alert_id, facility_slug=facility_slug).first()
        
        if not alert:
            return self.handle_error("Alert not found", 404)
        
        data = request.get_json()
        
        # Update fields
        if 'title' in data and data['title']:
            alert.title = Validators.sanitize_string(data['title'])
        if 'message' in data and data['message']:
            alert.message = Validators.sanitize_string(data['message'])
        if 'alert_type' in data:
            if data['alert_type'] not in Alert.ALERT_TYPES:
                return self.handle_error(f"Invalid alert_type. Must be one of: {', '.join(Alert.ALERT_TYPES)}", 400)
            alert.alert_type = data['alert_type']
        
        db.session.commit()
        
        return self.handle_response(
            data=alert.to_dict(),
            message="Alert updated successfully"
        )
    
    @role_required('ADMIN')
    def delete(self, alert_id):
        """Delete alert"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        alert = Alert.query.filter_by(id=alert_id, facility_slug=facility_slug).first()
        
        if not alert:
            return self.handle_error("Alert not found", 404)
        
        db.session.delete(alert)
        db.session.commit()
        
        return self.handle_response(message="Alert deleted successfully")


class AlertReadResource(BaseResource):
    """Resource for marking alerts as read"""
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')
    def put(self, alert_id):
        """Mark alert as read"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        alert = Alert.query.filter_by(id=alert_id, facility_slug=facility_slug).first()
        
        if not alert:
            return self.handle_error("Alert not found", 404)
        
        alert.mark_as_read()
        db.session.commit()
        
        return self.handle_response(
            data=alert.to_dict(),
            message="Alert marked as read"
        )


class AlertUnreadResource(BaseResource):
    """Resource for marking alerts as unread"""
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')
    def put(self, alert_id):
        """Mark alert as unread"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        alert = Alert.query.filter_by(id=alert_id, facility_slug=facility_slug).first()
        
        if not alert:
            return self.handle_error("Alert not found", 404)
        
        alert.mark_as_unread()
        db.session.commit()
        
        return self.handle_response(
            data=alert.to_dict(),
            message="Alert marked as unread"
        )


# Register resources
alert_ns.add_resource(AlertListResource, '')
alert_ns.add_resource(AlertResource, '/<string:alert_id>')
alert_ns.add_resource(AlertReadResource, '/<string:alert_id>/read')
alert_ns.add_resource(AlertUnreadResource, '/<string:alert_id>/unread')