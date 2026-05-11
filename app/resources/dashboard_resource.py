"""
Dashboard Routes - FastAPI Version
Converted from Flask-RESTx dashboard_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel, Field
from typing import Dict
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


class QueueStatus(BaseModel):
    waiting: int
    in_progress: int
    completed: int
    no_show: int


class DashboardStats(BaseModel):
    facility_slug: str
    patient_count: int
    today_appointments: int
    pending_lab_orders: int
    pending_radiology_orders: int
    low_inventory_items: int
    active_alerts: int
    queue_status: QueueStatus
    active_queue_count: int
    generated_at: str


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
        facility_slug: str = Query(None, description="Facility slug (required for non-admin)"),
        current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST'))
):
    """Get dashboard statistics for a facility"""
    try:
        # Determine facility - enforce user's facility for non-ADMINS
        if current_user.role != 'ADMIN' and current_user.facility_slug:
            facility_slug = current_user.facility_slug
        elif not facility_slug:
            raise HTTPException(status_code=400, detail="Facility slug is required")

        # Validate: non-admin users can only view their own facility
        if current_user.role != 'ADMIN' and facility_slug != current_user.facility_slug:
            raise HTTPException(status_code=403, detail="You can only view your own facility's data")

        # Get today's date range
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        # 1. Patient count
        patient_count = db_session.query(Patient).filter_by(facility_slug=facility_slug).count()

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

        # 6. Active alerts
        active_alerts = db_session.query(Alert).filter(
            Alert.facility_slug == facility_slug,
            Alert.is_read == False
        ).filter(
            or_(
                Alert.expires_at == None,
                Alert.expires_at > datetime.utcnow()
            )
        ).count()

        # 7. Queue status breakdown
        queue_status = QueueStatus(
            waiting=db_session.query(PatientQueue).filter_by(
                facility_slug=facility_slug, status='waiting'
            ).count(),
            in_progress=db_session.query(PatientQueue).filter_by(
                facility_slug=facility_slug, status='in_progress'
            ).count(),
            completed=db_session.query(PatientQueue).filter_by(
                facility_slug=facility_slug, status='completed'
            ).count(),
            no_show=db_session.query(PatientQueue).filter_by(
                facility_slug=facility_slug, status='no_show'
            ).count()
        )

        active_queue_count = queue_status.waiting + queue_status.in_progress

        return DashboardStats(
            facility_slug=facility_slug,
            patient_count=patient_count,
            today_appointments=today_appointments,
            pending_lab_orders=pending_lab_orders,
            pending_radiology_orders=pending_radiology_orders,
            low_inventory_items=low_inventory_items,
            active_alerts=active_alerts,
            queue_status=queue_status,
            active_queue_count=active_queue_count,
            generated_at=datetime.utcnow().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")