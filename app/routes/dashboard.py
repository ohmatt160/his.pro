"""
Dashboard Routes - FastAPI Version
Converted from Flask-RESTx dashboard_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
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
from app.utils.branch_scope import apply_branch_filter, effective_branch_id

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
    branch_id: str | None = Query(None, max_length=36),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard statistics for a facility"""
    try:
        if current_user.facility_slug != facility_slug:
            raise HTTPException(status_code=403, detail="You can only view your own facility's data")

        # Get today's date range
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        effective_department_id = effective_branch_id(current_user, branch_id, department_id)

        # 1. Patient count
        patient_query = db_session.query(Patient).filter_by(facility_slug=facility_slug)
        patient_query = apply_branch_filter(patient_query, Patient, effective_department_id)
        patient_count = patient_query.count()

        # 2. Today's appointments
        appointment_query = db_session.query(Appointment).filter(
            Appointment.facility_slug == facility_slug,
            Appointment.appointment_date >= today_start,
            Appointment.appointment_date < today_end
        )
        appointment_query = apply_branch_filter(appointment_query, Appointment, effective_department_id)
        today_appointments = appointment_query.count()

        # 3. Pending lab orders
        pending_lab_query = db_session.query(LabOrder).filter(
            LabOrder.facility_slug == facility_slug,
            LabOrder.status.in_(['ordered', 'collected', 'processing'])
        )
        pending_lab_orders = apply_branch_filter(pending_lab_query, LabOrder, effective_department_id).count()

        # 4. Pending radiology orders
        pending_radiology_query = db_session.query(Radiology).filter(
            Radiology.facility_slug == facility_slug,
            Radiology.status.in_(['pending', 'ordered'])
        )
        pending_radiology_orders = apply_branch_filter(pending_radiology_query, Radiology, effective_department_id).count()

        # 5. Low inventory items
        low_inventory_items = 0 if effective_department_id else db_session.query(Inventory).filter(
                Inventory.facility_slug == facility_slug,
                Inventory.is_active == True,
                Inventory.current_stock <= Inventory.reorder_level
            ).count()

        # 6. Active alerts (not read and not expired)
        active_alerts_query = db_session.query(Alert).filter(
            Alert.facility_slug == facility_slug,
            Alert.is_read == False
        ).filter(or_(Alert.expires_at == None, Alert.expires_at > datetime.utcnow()))
        if effective_department_id:
            active_alerts_query = active_alerts_query.filter(Alert.recipient_id == current_user.id)
        active_alerts = active_alerts_query.count()

        # 7. Queue status breakdown
        queue_query = db_session.query(PatientQueue).filter_by(facility_slug=facility_slug)
        queue_query = apply_branch_filter(queue_query, PatientQueue, effective_department_id)
        queue_rows = (
            queue_query.with_entities(PatientQueue.status, func.count(PatientQueue.id))
            .group_by(PatientQueue.status)
            .all()
        )
        queue_counts = {str(queue_status): int(count) for queue_status, count in queue_rows}
        queue_status = {
            'waiting': queue_counts.get('waiting', 0),
            'in_progress': queue_counts.get('in_progress', 0),
            'completed': queue_counts.get('completed', 0),
            'no_show': queue_counts.get('no_show', 0),
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
    except Exception:
        logger.exception("[Dashboard] Unexpected error while loading stats for %s", facility_slug)
        raise HTTPException(status_code=500, detail="Dashboard could not be loaded")
