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
from app.services.appointment_service import AppointmentService
from app.utils.validators import Validators
from app.utils.dependencies import get_current_user, role_required
from app.models.user import User
from app.models.patient import Patient
from app.models.facility import Facility

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/appointments", tags=["appointments"])


class AppointmentCreate(BaseModel):
    patient_id: str = Field(...)
    doctor_id: str = Field(...)
    appointment_date: str = Field(...)
    reason: Optional[str] = Field(None)
    notes: Optional[str] = Field(None)


class AppointmentUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(SCHEDULED|CONFIRMED|IN_PROGRESS|COMPLETED|CANCELLED|NO_SHOW)$")
    reason: Optional[str] = Field(None)
    notes: Optional[str] = Field(None)


class AppointmentResponse(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    appointment_date: str
    scheduled_time: Optional[str]
    duration_minutes: int
    status: str
    reason: Optional[str]
    notes: Optional[str]
    facility_slug: Optional[str]
    created_at: str
    updated_at: Optional[str]


class MessageResponse(BaseModel):
    message: str


@router.get("", response_model=List[AppointmentResponse])
async def get_appointments(
    patient_id: Optional[str] = Query(None),
    doctor_id: Optional[str] = Query(None),
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST')),
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
                raise HTTPException(status_code=404, detail="Patient not found")
            appointments = AppointmentService.get_appointments_by_patient(patient_id, facility_slug)
        elif doctor_id:
            appointments = AppointmentService.get_appointments_by_doctor(doctor_id, facility_slug)
        else:
            # Get all appointments for facility
            from app.models.appointment import Appointment
            appointments = db.query(Appointment).filter_by(facility_slug=facility_slug).order_by(Appointment.scheduled_time.desc()).all()

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
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST')),
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

        payload = data.dict()
        payload['facility_slug'] = facility_slug

        # Sanitize
        if payload.get('reason'):
            payload['reason'] = Validators.sanitize_string(payload['reason'])
        if payload.get('notes'):
            payload['notes'] = Validators.sanitize_string(payload['notes'])

        appointment = AppointmentService.create_appointment(payload)

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
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    try:
        facility_slug = current_user.facility_slug
        appointment = AppointmentService.get_appointment_by_id(appointment_id)

        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        if appointment.facility_slug != facility_slug:
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
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR')),
    db: Session = Depends(get_db)
):
    try:
        facility_slug = current_user.facility_slug
        appointment = AppointmentService.get_appointment_by_id(appointment_id)

        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        if appointment.facility_slug != facility_slug:
            raise HTTPException(status_code=404, detail="Appointment not found")

        payload = data.dict(exclude_unset=True)
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
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR')),
    db: Session = Depends(get_db)
):
    try:
        facility_slug = current_user.facility_slug
        appointment = AppointmentService.get_appointment_by_id(appointment_id)

        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        if appointment.facility_slug != facility_slug:
            raise HTTPException(status_code=404, detail="Appointment not found")

        cancelled = AppointmentService.cancel_appointment(appointment)

        return MessageResponse(message="Appointment cancelled successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Appointment] Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel appointment: {str(e)}")
