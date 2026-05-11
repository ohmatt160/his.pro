"""
Dashboard Routes - FastAPI Version
Converted from Flask-RESTx dashboard_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timedelta
import logging

from app.extensions import get_db, db_session
from app.utils.dependencies import get_current_user, role_required
from app.models.user import User
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.lab import LabOrder
from app.models.radiology import Radiology
from app.models.inventory import Inventory
from app.models.alert import Alert
from app.models.patient_queue import PatientQueue

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class DashboardStats(BaseModel):
    facility_slug: str
    patient_count: int
    today_appointments: int
    pending_lab_orders: int
    pending_radiology_orders: int
    low_inventory_items: int
    active_alerts: int
    queue_status: dict
    active_queue_count: int
    generated_at: str


@router.get("/stats")
async def get_dashboard_stats(
    facility_slug: str = Query(...),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard statistics for a facility"""
    try:
        # Non-ADMIN users can only view their own facility
        if current_user.role != 'ADMIN' and current_user.facility_slug != facility_slug:
            raise HTTPException(status_code=403, detail="You can only view your own facility's data")

        # Get today's date range
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        # Helper to get counts
        def count_query(model, **filters):
            return db_session.query(model).filter_by(**filters).count()

        # 1. Patient count
        patient_count = count_query(Patient, facility_slug=facility_slug)

        # 2. Today's appointments
        today_appointments = db_session.query(Appointment).filter(
            Appointment.facility_slug == facility_slug,
            Appointment.appointment_date >= today_start,
            Appointment.appointment_date < today_end
        ).count()

        # 3. Pending lab orders
        pending_lab_orders = db_session.query(LabOrder).filter(
            LabOrder.facility_slug == facility_slug,
            LabOrder.status.in_(['ordered', 'collected', 'processing'])
        ).count()

        # 4. Pending radiology orders
        pending_radiology_orders = db_session.query(Radiology).filter(
            Radiology.facility_slug == facility_slug,
            Radiology.status.in_(['pending', 'ordered'])
        ).count()

        # 5. Low inventory items
        low_inventory_items = db_session.query(Inventory).filter(
            Inventory.facility_slug == facility_slug,
            Inventory.is_active == True,
            Inventory.current_stock <= Inventory.reorder_level
        ).count()

        # 6. Active alerts (not read and not expired)
        active_alerts_query = db_session.query(Alert).filter(
            Alert.facility_slug == facility_slug,
            Alert.is_read == False
        ).filter(or_(Alert.expires_at == None, Alert.expires_at > datetime.utcnow()))
        active_alerts = active_alerts_query.count()

        # 7. Queue status breakdown
        queue_query = db_session.query(PatientQueue).filter_by(facility_slug=facility_slug)
        queue_status = {
            'waiting': queue_query.filter_by(status='waiting').count(),
            'in_progress': queue_query.filter_by(status='in_progress').count(),
            'completed': queue_query.filter_by(status='completed').count(),
            'no_show': queue_query.filter_by(status='no_show').count()
        }
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

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Dashboard] Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")
