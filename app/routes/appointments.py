"""
Appointments Routes - FastAPI Version
Converted from Flask-RESTx appointment_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from app.extensions import get_db
from app.schemas.appointments import AppointmentResponse, AppointmentCreate, AppointmentUpdate
from app.schemas.users import MessageResponse
from app.services.appointment_service import AppointmentService
from app.services.patient_notification_service import PatientNotificationService
from app.utils.validators import Validators
from app.utils.dependencies import get_current_user, role_required
from app.utils.branch_scope import apply_branch_filter, belongs_to_branch, effective_branch_id, ensure_patient_branch_access, require_tenant_row
from app.models.user import User
from app.models.patient import Patient
from app.models.facility import Facility

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/appointments", tags=["appointments"])




@router.get("", response_model=List[AppointmentResponse])
async def get_appointments(
    patient_id: Optional[str] = Query(None),
    doctor_id: Optional[str] = Query(None),
    department_id: Optional[str] = Query(None, max_length=36),
    branch_id: Optional[str] = Query(None, max_length=36),
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    try:
        facility_slug = current_user.facility_slug
        if not facility_slug:
            raise HTTPException(status_code=400, detail="User is not associated with a facility")

        if patient_id:
            # Verify patient belongs to facility
            patient = db.query(Patient).filter_by(id=patient_id, facility_slug=facility_slug).first()
            if not patient:
                return []
            appointments = AppointmentService.get_appointments_by_patient(patient_id, facility_slug)
        elif doctor_id:
            doctor = db.query(User).filter_by(id=doctor_id, facility_slug=facility_slug, is_active=True).first()
            if not doctor:
                return []
            appointments = AppointmentService.get_appointments_by_doctor(
                doctor_id,
                facility_slug=facility_slug,
            )
        else:
            # Get all appointments for facility
            from app.models.appointment import Appointment
            query = db.query(Appointment).filter_by(facility_slug=facility_slug)
            branch_scope_id = effective_branch_id(current_user, branch_id, department_id)
            query = apply_branch_filter(query, Appointment, branch_scope_id)
            appointments = query.order_by(Appointment.scheduled_time.desc()).all()

        branch_scope_id = effective_branch_id(current_user, branch_id, department_id)
        if branch_scope_id:
            appointments = [a for a in appointments if belongs_to_branch(a, branch_scope_id)]

        return [
            AppointmentResponse(
                id=str(a.id),
                patient_id=str(a.patient_id),
                doctor_id=str(a.doctor_id),
                appointment_date=a.appointment_date.isoformat() if a.appointment_date else "",
                scheduled_time=a.scheduled_time.isoformat() if a.scheduled_time else None,
                duration_minutes=a.duration_minutes or 30,
                status=a.status,
                reason=a.reason,
                notes=a.notes,
                facility_slug=a.facility_slug,
                department_id=a.department_id,
                branch_id=a.branch_id or a.department_id,
                created_at=a.created_at.isoformat() if a.created_at else "",
                updated_at=a.updated_at.isoformat() if a.updated_at else None
            ) for a in appointments
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Appointment] Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve appointments: {str(e)}")


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    data: AppointmentCreate,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    try:
        facility_slug = current_user.facility_slug
        if not facility_slug:
            raise HTTPException(status_code=400, detail="User is not associated with a facility")

        # Verify patient belongs to facility
        patient = db.query(Patient).filter_by(id=data.patient_id, facility_slug=facility_slug).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        ensure_patient_branch_access(patient, current_user, data.branch_id or data.department_id)

        doctor = db.query(User).filter_by(id=data.doctor_id, facility_slug=facility_slug, is_active=True).first()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor or staff member not found")
        require_tenant_row(doctor, current_user, "Doctor or staff member not found")

        payload = data.model_dump()
        payload['facility_slug'] = facility_slug
        resolved_branch_id = current_user.branch_id or payload.get('branch_id') or patient.branch_id or doctor.branch_id
        legacy_branch_id = current_user.department_id or payload.get('department_id') or patient.department_id or doctor.department_id
        payload['branch_id'] = resolved_branch_id or legacy_branch_id
        payload['department_id'] = payload.get('department_id') or legacy_branch_id

        # Sanitize
        if payload.get('reason'):
            payload['reason'] = Validators.sanitize_string(payload['reason'])
        if payload.get('notes'):
            payload['notes'] = Validators.sanitize_string(payload['notes'])

        appointment = AppointmentService.create_appointment(payload)
        PatientNotificationService.create(
            facility_slug=facility_slug,
            patient=patient,
            notification_type="appointment_reminder",
            title="Appointment reminder",
            message=f"Your appointment is scheduled for {appointment.appointment_date.isoformat()}.",
            source_type="appointment",
            source_id=appointment.id,
            metadata={
                "appointment_date": appointment.appointment_date.isoformat() if appointment.appointment_date else None,
                "doctor_id": appointment.doctor_id,
            },
        )

        return AppointmentResponse(
            id=str(appointment.id),
            patient_id=str(appointment.patient_id),
            doctor_id=str(appointment.doctor_id),
            appointment_date=appointment.appointment_date.isoformat() if appointment.appointment_date else "",
            scheduled_time=appointment.scheduled_time.isoformat() if appointment.scheduled_time else None,
            duration_minutes=appointment.duration_minutes or 30,
            status=appointment.status,
            reason=appointment.reason,
            notes=appointment.notes,
            facility_slug=appointment.facility_slug,
            department_id=appointment.department_id,
            branch_id=appointment.branch_id or appointment.department_id,
            created_at=appointment.created_at.isoformat() if appointment.created_at else "",
            updated_at=appointment.updated_at.isoformat() if appointment.updated_at else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Appointment] Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create appointment: {str(e)}")


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: str,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    try:
        facility_slug = current_user.facility_slug
        appointment = AppointmentService.get_appointment_by_id(appointment_id)

        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        if appointment.facility_slug != facility_slug:
            raise HTTPException(status_code=404, detail="Appointment not found")

        branch_scope_id = effective_branch_id(current_user)
        if branch_scope_id and not belongs_to_branch(appointment, branch_scope_id):
            raise HTTPException(status_code=404, detail="Appointment not found")

        return AppointmentResponse(
            id=str(appointment.id),
            patient_id=str(appointment.patient_id),
            doctor_id=str(appointment.doctor_id),
            appointment_date=appointment.appointment_date.isoformat() if appointment.appointment_date else "",
            scheduled_time=appointment.scheduled_time.isoformat() if appointment.scheduled_time else None,
            duration_minutes=appointment.duration_minutes or 30,
            status=appointment.status,
            reason=appointment.reason,
            notes=appointment.notes,
            facility_slug=appointment.facility_slug,
            department_id=appointment.department_id,
            branch_id=appointment.branch_id or appointment.department_id,
            created_at=appointment.created_at.isoformat() if appointment.created_at else "",
            updated_at=appointment.updated_at.isoformat() if appointment.updated_at else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Appointment] Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve appointment: {str(e)}")


@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: str,
    data: AppointmentUpdate,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR')),
    db: Session = Depends(get_db)
):
    try:
        facility_slug = current_user.facility_slug
        appointment = AppointmentService.get_appointment_by_id(appointment_id)

        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        if appointment.facility_slug != facility_slug:
            raise HTTPException(status_code=404, detail="Appointment not found")

        branch_scope_id = effective_branch_id(current_user)
        if branch_scope_id and not belongs_to_branch(appointment, branch_scope_id):
            raise HTTPException(status_code=404, detail="Appointment not found")

        payload = data.model_dump(exclude_unset=True)
        if 'status' in payload:
            updated_appointment = AppointmentService.update_appointment_status(appointment, payload['status'])
        else:
            updated_appointment = AppointmentService.update_appointment(appointment, payload)

        return AppointmentResponse(
            id=str(updated_appointment.id),
            patient_id=str(updated_appointment.patient_id),
            doctor_id=str(updated_appointment.doctor_id),
            appointment_date=updated_appointment.appointment_date.isoformat() if updated_appointment.appointment_date else "",
            scheduled_time=updated_appointment.scheduled_time.isoformat() if updated_appointment.scheduled_time else None,
            duration_minutes=updated_appointment.duration_minutes or 30,
            status=updated_appointment.status,
            reason=updated_appointment.reason,
            notes=updated_appointment.notes,
            facility_slug=updated_appointment.facility_slug,
            department_id=updated_appointment.department_id,
            branch_id=updated_appointment.branch_id or updated_appointment.department_id,
            created_at=updated_appointment.created_at.isoformat() if updated_appointment.created_at else "",
            updated_at=updated_appointment.updated_at.isoformat() if updated_appointment.updated_at else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Appointment] Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update appointment: {str(e)}")


@router.delete("/{appointment_id}", response_model=MessageResponse)
async def cancel_appointment(
    appointment_id: str,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR')),
    db: Session = Depends(get_db)
):
    try:
        facility_slug = current_user.facility_slug
        appointment = AppointmentService.get_appointment_by_id(appointment_id)

        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        if appointment.facility_slug != facility_slug:
            raise HTTPException(status_code=404, detail="Appointment not found")

        branch_scope_id = effective_branch_id(current_user)
        if branch_scope_id and not belongs_to_branch(appointment, branch_scope_id):
            raise HTTPException(status_code=404, detail="Appointment not found")

        cancelled = AppointmentService.cancel_appointment(appointment)

        return MessageResponse(message="Appointment cancelled successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Appointment] Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel appointment: {str(e)}")
