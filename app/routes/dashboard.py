"""
Dashboard Routes - FastAPI Version
Converted from Flask-RESTx dashboard_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
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
from app.schemas.dashboard import DashboardStats

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _empty_dashboard_stats(facility_slug: str) -> dict:
    return {
        'facility_slug': facility_slug,
        'patient_count': 0,
        'today_appointments': 0,
        'pending_lab_orders': 0,
        'pending_radiology_orders': 0,
        'low_inventory_items': 0,
        'active_alerts': 0,
        'queue_status': {
            'waiting': 0,
            'in_progress': 0,
            'completed': 0,
            'no_show': 0,
        },
        'active_queue_count': 0,
        'generated_at': datetime.utcnow().isoformat(),
    }


@router.get("/stats")
async def get_dashboard_stats(
    facility_slug: str = Query(...),
    department_id: str | None = Query(None, max_length=36),
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

        effective_department_id = current_user.department_id if current_user.role != "ADMIN" else department_id

        # 1. Patient count
        patient_query = db_session.query(Patient).filter_by(facility_slug=facility_slug)
        if effective_department_id:
            patient_query = patient_query.filter_by(department_id=effective_department_id)
        patient_count = patient_query.count()

        # 2. Today's appointments
        appointment_query = db_session.query(Appointment).filter(
            Appointment.facility_slug == facility_slug,
            Appointment.appointment_date >= today_start,
            Appointment.appointment_date < today_end
        )
        if effective_department_id:
            appointment_query = appointment_query.filter(Appointment.department_id == effective_department_id)
        today_appointments = appointment_query.count()

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
    except SQLAlchemyError as e:
        logger.warning("[Dashboard] Returning empty stats for %s after database read failed: %s", facility_slug, e, exc_info=True)
        db_session.rollback()
        return _empty_dashboard_stats(facility_slug)
    except Exception as e:
        logger.error(f"[Dashboard] Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")
