"""
Queue Management Routes - FastAPI Version
Converted from Flask-RESTx queue_resource.py
"""

from fastapi import APIRouter, Depends, Header, HTTPException, status, Query, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import case
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from app.extensions import get_db, db_session
from app.schemas.queue import QueueListResponse, QueueResponse, QueueCreate, QueueUpdate
from app.schemas.users import MessageResponse
from app.utils.dependencies import get_current_user, role_required
from app.utils.branch_scope import apply_branch_filter, belongs_to_branch, effective_branch_id
from app.models.user import User
from app.models.patient_queue import PatientQueue
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.services.realtime_service import publish_tenant_event
from app.utils.validators import Validators
from app.utils.idempotency import (
    IdempotencyConflictError,
    idempotency_payload_hash,
    require_idempotency_key,
    verify_idempotent_replay,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/queue", tags=["queue"])


def _publish_queue_event(event_type: str, entry: PatientQueue) -> None:
    publish_tenant_event(
        event_type=event_type,
        facility_slug=entry.facility_slug,
        branch_id=entry.branch_id or getattr(entry, "department_id", None),
        roles=["ADMIN", "BRANCH_ADMIN", "DOCTOR", "NURSE", "RECEPTIONIST"],
        modules=["reception", "consultations", "nursing"],
        resource_id=entry.id,
        payload={"status": entry.status, "patient_id": entry.patient_id},
    )


def _queue_response(entry: PatientQueue, patient: Patient | None = None) -> QueueResponse:
    patient = patient or entry.patient
    return QueueResponse(
        id=str(entry.id),
        patient_id=str(entry.patient_id),
        patient_name=patient.full_name if patient else None,
        patient_phone=patient.phone if patient else None,
        patient_date_of_birth=(
            patient.date_of_birth.isoformat()
            if patient and patient.date_of_birth
            else None
        ),
        appointment_id=str(entry.appointment_id) if entry.appointment_id else None,
        appointment_time=(
            entry.appointment.appointment_date.isoformat()
            if entry.appointment and entry.appointment.appointment_date
            else None
        ),
        facility_slug=entry.facility_slug,
        department=entry.department,
        branch_id=entry.branch_id,
        status=entry.status,
        queue_number=entry.queue_number,
        priority=entry.priority,
        checked_in_at=entry.checked_in_at.isoformat() if entry.checked_in_at else None,
        started_at=entry.started_at.isoformat() if entry.started_at else None,
        completed_at=entry.completed_at.isoformat() if entry.completed_at else None,
        created_at=entry.created_at.isoformat() if entry.created_at else "",
    )




...

@router.get("", response_model=QueueListResponse)
async def get_queue(
    status: Optional[str] = Query(None, pattern="^(waiting|in_progress|completed|no_show)$"),
    department: Optional[str] = Query(None, max_length=100),
    branch_id: Optional[str] = Query(None, max_length=36),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    """Get queue entries for user's facility"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    query = (
        db_session.query(PatientQueue)
        .options(joinedload(PatientQueue.patient), joinedload(PatientQueue.appointment))
        .filter_by(facility_slug=facility_slug)
    )

    if status:
        query = query.filter_by(status=status)
    if department:
        query = query.filter_by(department=department)
    branch_scope_id = effective_branch_id(current_user, branch_id)
    query = apply_branch_filter(query, PatientQueue, branch_scope_id)

    query = query.order_by(
        case((PatientQueue.priority == 'urgent', 1), else_=2),
        PatientQueue.queue_number
    )

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page

    entries = []
    for entry in items:
        entries.append(QueueResponse(
            id=str(entry.id),
            patient_id=str(entry.patient_id),
            patient_name=entry.patient.full_name if entry.patient else None,
            patient_phone=entry.patient.phone if entry.patient else None,
            patient_date_of_birth=entry.patient.date_of_birth.isoformat() if entry.patient and entry.patient.date_of_birth else None,
            appointment_id=str(entry.appointment_id) if entry.appointment_id else None,
            appointment_time=entry.appointment.appointment_date.isoformat() if entry.appointment and entry.appointment.appointment_date else None,
            facility_slug=entry.facility_slug,
            department=entry.department,
            branch_id=entry.branch_id,
            status=entry.status,
            queue_number=entry.queue_number,
            priority=entry.priority,
            checked_in_at=entry.checked_in_at.isoformat() if entry.checked_in_at else None,
            started_at=entry.started_at.isoformat() if entry.started_at else None,
            completed_at=entry.completed_at.isoformat() if entry.completed_at else None,
            created_at=entry.created_at.isoformat() if entry.created_at else ""
        ))

    return QueueListResponse(
        queue_entries=entries,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.post("", response_model=QueueResponse, status_code=status.HTTP_201_CREATED)
async def add_to_queue(
    data: QueueCreate,
    response: Response,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    """Add patient to queue"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")
    idempotency_key = require_idempotency_key(idempotency_key)
    payload_hash = idempotency_payload_hash({
        "facility_slug": facility_slug,
        "queue": data.model_dump(),
    })
    existing_idempotent = db_session.query(PatientQueue).filter_by(
        facility_slug=facility_slug,
        idempotency_key=idempotency_key,
    ).first()
    if existing_idempotent:
        try:
            verify_idempotent_replay(existing_idempotent, payload_hash)
        except IdempotencyConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        response.status_code = status.HTTP_200_OK
        return _queue_response(existing_idempotent)

    # Verify patient exists and belongs to facility
    patient = db_session.query(Patient).filter_by(id=data.patient_id, facility_slug=facility_slug).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    appointment = None
    # Verify appointment if provided
    if data.appointment_id:
        appointment = db_session.query(Appointment).filter_by(id=data.appointment_id, facility_slug=facility_slug).first()
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

    branch_scope_id = effective_branch_id(current_user, data.branch_id) or data.branch_id or patient.branch_id or patient.department_id
    if branch_scope_id and not belongs_to_branch(patient, branch_scope_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    if appointment and branch_scope_id and not belongs_to_branch(appointment, branch_scope_id):
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Check if patient already in queue with active status
    existing_query = db_session.query(PatientQueue).filter(
        PatientQueue.patient_id == data.patient_id,
        PatientQueue.facility_slug == facility_slug,
        PatientQueue.status.in_(['waiting', 'in_progress'])
    )
    existing_query = apply_branch_filter(existing_query, PatientQueue, branch_scope_id)
    existing = existing_query.first()
    if existing:
        raise HTTPException(status_code=400, detail="Patient is already in queue")

    # Get next queue number
    last_entry_query = db_session.query(PatientQueue).filter_by(
        facility_slug=facility_slug,
        department=data.department
    )
    last_entry_query = apply_branch_filter(last_entry_query, PatientQueue, branch_scope_id)
    last_entry = last_entry_query.order_by(PatientQueue.queue_number.desc()).first()

    next_number = (last_entry.queue_number + 1) if last_entry else 1

    # Sanitize department
    department = Validators.sanitize_string(data.department)

    # Create queue entry
    queue_entry = PatientQueue(
        facility_id=current_user.facility_id,
        facility_slug=facility_slug,
        patient_id=data.patient_id,
        appointment_id=data.appointment_id,
        branch_id=branch_scope_id,
        department=department,
        priority=data.priority,
        queue_number=next_number,
        status='waiting',
        idempotency_key=idempotency_key,
        idempotency_payload_hash=payload_hash,
    )
    try:
        db_session.add(queue_entry)
        db_session.commit()
        db_session.refresh(queue_entry)
    except IntegrityError:
        db_session.rollback()
        replay = db_session.query(PatientQueue).filter_by(
            facility_slug=facility_slug,
            idempotency_key=idempotency_key,
        ).first()
        if replay:
            try:
                verify_idempotent_replay(replay, payload_hash)
            except IdempotencyConflictError as exc:
                raise HTTPException(status_code=409, detail=str(exc))
            response.status_code = status.HTTP_200_OK
            return _queue_response(replay)
        active = db_session.query(PatientQueue).filter(
            PatientQueue.facility_slug == facility_slug,
            PatientQueue.patient_id == data.patient_id,
            PatientQueue.status.in_(['waiting', 'in_progress']),
        ).first()
        if active:
            raise HTTPException(status_code=409, detail="Patient is already in queue")
        raise
    _publish_queue_event("queue.created", queue_entry)

    return _queue_response(queue_entry, patient)


@router.get("/{queue_id}", response_model=QueueResponse)
async def get_queue_entry(
    queue_id: str,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    """Get queue entry by ID"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    entry = db_session.query(PatientQueue).filter_by(id=queue_id, facility_slug=facility_slug).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")

    branch_scope_id = effective_branch_id(current_user)
    if branch_scope_id and not belongs_to_branch(entry, branch_scope_id):
        raise HTTPException(status_code=404, detail="Queue entry not found")

    return QueueResponse(
        id=str(entry.id),
        patient_id=str(entry.patient_id),
        patient_name=entry.patient.full_name if entry.patient else None,
        patient_phone=entry.patient.phone if entry.patient else None,
        patient_date_of_birth=entry.patient.date_of_birth.isoformat() if entry.patient and entry.patient.date_of_birth else None,
        appointment_id=str(entry.appointment_id) if entry.appointment_id else None,
        appointment_time=entry.appointment.scheduled_time.isoformat() if entry.appointment and entry.appointment.scheduled_time else None,
        facility_slug=entry.facility_slug,
        department=entry.department,
        status=entry.status,
        queue_number=entry.queue_number,
        priority=entry.priority,
        checked_in_at=entry.checked_in_at.isoformat() if entry.checked_in_at else None,
        started_at=entry.started_at.isoformat() if entry.started_at else None,
        completed_at=entry.completed_at.isoformat() if entry.completed_at else None,
        created_at=entry.created_at.isoformat() if entry.created_at else ""
    )


@router.put("/{queue_id}", response_model=QueueResponse)
async def update_queue_entry(
    queue_id: str,
    data: QueueUpdate,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE')),
    db: Session = Depends(get_db)
):
    """Update queue entry"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    entry = db_session.query(PatientQueue).filter_by(id=queue_id, facility_slug=facility_slug).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")

    branch_scope_id = effective_branch_id(current_user)
    if branch_scope_id and not belongs_to_branch(entry, branch_scope_id):
        raise HTTPException(status_code=404, detail="Queue entry not found")

    if data.status is not None:
        if data.status not in PatientQueue.STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(PatientQueue.STATUSES)}")
        entry.status = data.status
    if data.priority is not None:
        if data.priority not in PatientQueue.PRIORITIES:
            raise HTTPException(status_code=400, detail=f"Invalid priority. Must be one of: {', '.join(PatientQueue.PRIORITIES)}")
        entry.priority = data.priority
    if data.department is not None:
        entry.department = Validators.sanitize_string(data.department)

    entry.save()
    db_session.commit()
    _publish_queue_event("queue.updated", entry)

    return QueueResponse(
        id=str(entry.id),
        patient_id=str(entry.patient_id),
        patient_name=entry.patient.full_name if entry.patient else None,
        patient_phone=entry.patient.phone if entry.patient else None,
        patient_date_of_birth=entry.patient.date_of_birth.isoformat() if entry.patient and entry.patient.date_of_birth else None,
        appointment_id=str(entry.appointment_id) if entry.appointment_id else None,
        appointment_time=entry.appointment.scheduled_time.isoformat() if entry.appointment and entry.appointment.scheduled_time else None,
        facility_slug=entry.facility_slug,
        department=entry.department,
        status=entry.status,
        queue_number=entry.queue_number,
        priority=entry.priority,
        checked_in_at=entry.checked_in_at.isoformat() if entry.checked_in_at else None,
        started_at=entry.started_at.isoformat() if entry.started_at else None,
        completed_at=entry.completed_at.isoformat() if entry.completed_at else None,
        created_at=entry.created_at.isoformat() if entry.created_at else ""
    )


@router.delete("/{queue_id}", response_model=MessageResponse)
async def remove_from_queue(
    queue_id: str,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    """Remove patient from queue"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    entry = db_session.query(PatientQueue).filter_by(id=queue_id, facility_slug=facility_slug).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")

    branch_scope_id = effective_branch_id(current_user)
    if branch_scope_id and not belongs_to_branch(entry, branch_scope_id):
        raise HTTPException(status_code=404, detail="Queue entry not found")

    if entry.status == 'in_progress':
        raise HTTPException(status_code=400, detail="Cannot remove patient whose visit is in progress")

    _publish_queue_event("queue.deleted", entry)
    db_session.delete(entry)
    db_session.commit()

    return MessageResponse(message="Patient removed from queue successfully")


@router.put("/{queue_id}/checkin", response_model=QueueResponse)
async def check_in_patient(
    queue_id: str,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    """Check in patient"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    entry = db_session.query(PatientQueue).filter_by(id=queue_id, facility_slug=facility_slug).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")

    branch_scope_id = effective_branch_id(current_user)
    if branch_scope_id and not belongs_to_branch(entry, branch_scope_id):
        raise HTTPException(status_code=404, detail="Queue entry not found")

    if entry.status != 'waiting':
        raise HTTPException(status_code=400, detail="Patient cannot be checked in")

    entry.check_in()
    entry.save()
    db_session.commit()
    _publish_queue_event("queue.checked_in", entry)

    return QueueResponse(
        id=str(entry.id),
        patient_id=str(entry.patient_id),
        patient_name=entry.patient.full_name if entry.patient else None,
        patient_phone=entry.patient.phone if entry.patient else None,
        patient_date_of_birth=entry.patient.date_of_birth.isoformat() if entry.patient and entry.patient.date_of_birth else None,
        appointment_id=str(entry.appointment_id) if entry.appointment_id else None,
        appointment_time=entry.appointment.scheduled_time.isoformat() if entry.appointment and entry.appointment.scheduled_time else None,
        facility_slug=entry.facility_slug,
        department=entry.department,
        status=entry.status,
        queue_number=entry.queue_number,
        priority=entry.priority,
        checked_in_at=entry.checked_in_at.isoformat() if entry.checked_in_at else None,
        started_at=entry.started_at.isoformat() if entry.started_at else None,
        completed_at=entry.completed_at.isoformat() if entry.completed_at else None,
        created_at=entry.created_at.isoformat() if entry.created_at else ""
    )


@router.put("/{queue_id}/start", response_model=QueueResponse)
async def start_visit(
    queue_id: str,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    """Start patient visit"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    entry = db_session.query(PatientQueue).filter_by(id=queue_id, facility_slug=facility_slug).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")

    branch_scope_id = effective_branch_id(current_user)
    if branch_scope_id and not belongs_to_branch(entry, branch_scope_id):
        raise HTTPException(status_code=404, detail="Queue entry not found")

    if entry.status != 'waiting':
        raise HTTPException(status_code=400, detail="Patient is not in waiting status")

    entry.start_visit()
    entry.save()
    db_session.commit()
    _publish_queue_event("queue.started", entry)

    return QueueResponse(
        id=str(entry.id),
        patient_id=str(entry.patient_id),
        patient_name=entry.patient.full_name if entry.patient else None,
        patient_phone=entry.patient.phone if entry.patient else None,
        patient_date_of_birth=entry.patient.date_of_birth.isoformat() if entry.patient and entry.patient.date_of_birth else None,
        appointment_id=str(entry.appointment_id) if entry.appointment_id else None,
        appointment_time=entry.appointment.scheduled_time.isoformat() if entry.appointment and entry.appointment.scheduled_time else None,
        facility_slug=entry.facility_slug,
        department=entry.department,
        status=entry.status,
        queue_number=entry.queue_number,
        priority=entry.priority,
        checked_in_at=entry.checked_in_at.isoformat() if entry.checked_in_at else None,
        started_at=entry.started_at.isoformat() if entry.started_at else None,
        completed_at=entry.completed_at.isoformat() if entry.completed_at else None,
        created_at=entry.created_at.isoformat() if entry.created_at else ""
    )


@router.put("/{queue_id}/complete", response_model=QueueResponse)
async def complete_visit(
    queue_id: str,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    """Complete patient visit"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    entry = db_session.query(PatientQueue).filter_by(id=queue_id, facility_slug=facility_slug).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")

    branch_scope_id = effective_branch_id(current_user)
    if branch_scope_id and not belongs_to_branch(entry, branch_scope_id):
        raise HTTPException(status_code=404, detail="Queue entry not found")

    if entry.status not in {'waiting', 'in_progress'}:
        raise HTTPException(status_code=400, detail="Patient cannot be cleared from the queue")

    if entry.status == 'waiting':
        entry.start_visit()

    entry.complete_visit()
    entry.save()
    db_session.commit()
    _publish_queue_event("queue.completed", entry)

    return QueueResponse(
        id=str(entry.id),
        patient_id=str(entry.patient_id),
        patient_name=entry.patient.full_name if entry.patient else None,
        patient_phone=entry.patient.phone if entry.patient else None,
        patient_date_of_birth=entry.patient.date_of_birth.isoformat() if entry.patient and entry.patient.date_of_birth else None,
        appointment_id=str(entry.appointment_id) if entry.appointment_id else None,
        appointment_time=entry.appointment.scheduled_time.isoformat() if entry.appointment and entry.appointment.scheduled_time else None,
        facility_slug=entry.facility_slug,
        department=entry.department,
        status=entry.status,
        queue_number=entry.queue_number,
        priority=entry.priority,
        checked_in_at=entry.checked_in_at.isoformat() if entry.checked_in_at else None,
        started_at=entry.started_at.isoformat() if entry.started_at else None,
        completed_at=entry.completed_at.isoformat() if entry.completed_at else None,
        created_at=entry.created_at.isoformat() if entry.created_at else ""
    )
