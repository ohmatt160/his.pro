from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.resources.base_resource import BaseResource
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.lab import LabOrder
from app.models.radiology import Radiology
from app.models.inventory import Inventory
from app.models.alert import Alert
from app.models.patient_queue import PatientQueue
from app.utils.decorators import role_required
from app.extensions import db
from datetime import datetime, timedelta

dashboard_ns = Namespace('dashboard', description='Dashboard statistics operations')

# Swagger model for stats
dashboard_stats_model = dashboard_ns.model('DashboardStats', {
    'facility_slug': fields.String(required=True),
    'patient_count': fields.Integer(),
    'today_appointments': fields.Integer(),
    'pending_lab_orders': fields.Integer(),
    'pending_radiology_orders': fields.Integer(),
    'low_inventory_items': fields.Integer(),
    'active_alerts': fields.Integer(),
    'queue_status': fields.Raw()
})


class DashboardStatsResource(BaseResource):
    """Resource for dashboard statistics"""
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')
    def get(self):
        """Get dashboard statistics for a facility"""
        try:
            # Get facility_slug from query params
            facility_slug = request.args.get('facility_slug')
            
            # Get current user
            current_user = self.get_current_user()
            print(f"[Dashboard] User: {current_user.username if current_user else 'None'}, role: {current_user.role if current_user else 'None'}, facility: {current_user.facility_slug if current_user else 'None'}")
            print(f"[Dashboard] Requested facility_slug: {facility_slug}")
            
            # Determine facility - enforce user's facility for non-ADMINS
            if current_user.role != 'ADMIN' and current_user.facility_slug:
                facility_slug = current_user.facility_slug
            elif not facility_slug:
                return self.handle_error("Facility slug is required", 400)
            
            # Validate: non-admin users can only view their own facility
            if current_user.role != 'ADMIN' and facility_slug != current_user.facility_slug:
                return self.handle_error("You can only view your own facility's data", 403)
            
            # Get today's date range
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            # 1. Patient count
            patient_count = Patient.query.filter_by(facility_slug=facility_slug).count()
            
            # 2. Today's appointments
            today_appointments = Appointment.query.filter(
                Appointment.facility_slug == facility_slug,
                Appointment.appointment_date >= today_start,
                Appointment.appointment_date < today_end
            ).count()
            
            # 3. Pending lab orders
            pending_lab_orders = LabOrder.query.filter(
                LabOrder.facility_slug == facility_slug,
                LabOrder.status.in_(['ordered', 'collected', 'processing'])
            ).count()
            
            # 4. Pending radiology orders
            pending_radiology_orders = Radiology.query.filter(
                Radiology.facility_slug == facility_slug,
                Radiology.status.in_(['pending', 'ordered'])
            ).count()
            
            # 5. Low inventory items
            low_inventory_items = Inventory.query.filter(
                Inventory.facility_slug == facility_slug,
                Inventory.is_active == True,
                Inventory.current_stock <= Inventory.reorder_level
            ).count()
            
            # 6. Active alerts (not read and not expired)
            active_alerts = Alert.query.filter(
                Alert.facility_slug == facility_slug,
                Alert.is_read == False
            ).filter(
                db.or_(
                    Alert.expires_at == None,
                    Alert.expires_at > datetime.utcnow()
                )
            ).count()
            
            # 7. Queue status breakdown
            queue_status_query = PatientQueue.query.filter_by(facility_slug=facility_slug)
            queue_status = {
                'waiting': queue_status_query.filter_by(status='waiting').count(),
                'in_progress': queue_status_query.filter_by(status='in_progress').count(),
                'completed': queue_status_query.filter_by(status='completed').count(),
                'no_show': queue_status_query.filter_by(status='no_show').count()
            }
            
            # Get waiting and in_progress counts for total active queue
            active_queue_count = queue_status['waiting'] + queue_status['in_progress']
            
            stats = {
                'facility_slug': facility_slug,
                'patient_count': patient_count,
                'today_appointments': today_appointments,
                'pending_lab_orders': pending_lab_orders,
                'pending_radiology_orders': pending_radiology_orders,
                'low_inventory_items': low_inventory_items,
                'active_alerts': active_alerts,
                'queue_status': queue_status,
                'active_queue_count': active_queue_count,
                'generated_at': datetime.utcnow().isoformat()
            }
            
            return self.handle_response(data=stats)
        except Exception as e:
            import traceback
            print(f"[Dashboard] Exception: {str(e)}")
            traceback.print_exc()
            return self.handle_error(f"Dashboard error: {str(e)}", 500)


# Register resources
dashboard_ns.add_resource(DashboardStatsResource, '/stats')