"""
Radiology Routes - FastAPI Version
Converted from Flask-RESTx radiology_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging

from app.extensions import get_db, db_session
from app.schemas.radiology import RadiologyResponse, RadiologyCreate, RadiologyUpdate, RadiologyReport
from app.services.clinical_workflow_service import ClinicalWorkflowService
from app.services.order_workflow_service import OrderWorkflowService
from app.services.patient_notification_service import PatientNotificationService
from app.utils.dependencies import get_current_user, role_required
from app.utils.validators import Validators
from app.models.user import User
from app.models.patient import Patient
from app.models.radiology import Radiology

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/radiology", tags=["radiology"])


def _full_name(user_or_patient):
    if not user_or_patient:
        return None
    first_name = user_or_patient.first_name or ""
    last_name = user_or_patient.last_name or ""
    return f"{first_name} {last_name}".strip() or None


def _radiology_response(order: Radiology) -> RadiologyResponse:
    return RadiologyResponse(
        id=str(order.id),
        patient_id=str(order.patient_id),
        facility_slug=order.facility_slug,
        modality=order.modality,
        body_part=order.body_part,
        clinical_notes=order.clinical_notes,
        status=order.status,
        requested_by=str(order.requested_by),
        radiologist_id=str(order.radiologist_id) if order.radiologist_id else None,
        report=order.report,
        report_date=order.report_date.isoformat() if order.report_date else None,
        request_date=order.request_date.isoformat() if order.request_date else "",
        patient_name=_full_name(order.patient),
        requested_by_name=_full_name(order.requester),
        radiologist_name=_full_name(order.radiologist)
    )


@router.get("", response_model=List[RadiologyResponse])
async def get_radiology_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    facility_slug: Optional[str] = Query(None),
    status: Optional[str] = Query(None, pattern="^(pending|ordered|completed|cancelled)$"),
    patient_id: Optional[str] = Query(None),
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'RADIOLOGIST')),
    db: Session = Depends(get_db)
):
    """Paginated list of radiology orders"""
    if not current_user.facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    query = db_session.query(Radiology).options(
        joinedload(Radiology.patient),
        joinedload(Radiology.requester),
        joinedload(Radiology.radiologist),
    ).filter_by(facility_slug=current_user.facility_slug)

    if status:
        query = query.filter_by(status=status)
    if patient_id:
        patient = db_session.query(Patient).filter_by(
            id=patient_id,
            facility_slug=current_user.facility_slug,
        ).first()
        if not patient:
            return []
        query = query.filter_by(patient_id=patient_id)

    query = query.order_by(Radiology.request_date.desc())

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page

    return [_radiology_response(order) for order in items]


@router.post("", response_model=RadiologyResponse, status_code=status.HTTP_201_CREATED)
async def create_radiology_order(
    data: RadiologyCreate,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR')),
    db: Session = Depends(get_db)
):
    """Create a new radiology order"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    if not data.patient_id or not data.modality or not data.body_part:
        raise HTTPException(status_code=400, detail="Missing required fields")

    patient = db_session.query(Patient).filter_by(id=data.patient_id, facility_slug=facility_slug).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Validate modality
    Radiology.MODALITIES
    if data.modality not in Radiology.MODALITIES:
        raise HTTPException(status_code=400, detail=f"Invalid modality. Must be one of: {', '.join(Radiology.MODALITIES)}")

    # Sanitize notes
    clinical_notes = Validators.sanitize_string(data.clinical_notes or '')

    radiology = Radiology(
        patient_id=data.patient_id,
        facility_slug=facility_slug,
        modality=data.modality,
        body_part=data.body_part,
        clinical_notes=clinical_notes,
        requested_by=current_user.id,
        status='pending'
    )
    db_session.add(radiology)
    db_session.flush()
    OrderWorkflowService.record(
        facility_slug=facility_slug,
        patient_id=radiology.patient_id,
        order_type="radiology",
        order_id=radiology.id,
        event_type="consultation_order_created",
        status=radiology.status,
        title="Radiology order created",
        message=f"{radiology.modality} {radiology.body_part} order created.",
        actor_id=current_user.id,
        target_role="RADIOLOGIST",
        metadata={"modality": radiology.modality, "body_part": radiology.body_part},
    )
    db_session.commit()
    db_session.refresh(radiology)

    radiology.patient = patient
    radiology.requester = current_user
    return _radiology_response(radiology)


@router.get("/{order_id}", response_model=RadiologyResponse)
async def get_radiology_order(
    order_id: str,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'RADIOLOGIST')),
    db: Session = Depends(get_db)
):
    """Get radiology order by ID"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    order = db_session.query(Radiology).options(
        joinedload(Radiology.patient),
        joinedload(Radiology.requester),
        joinedload(Radiology.radiologist),
    ).filter_by(id=order_id, facility_slug=facility_slug).first()
    if not order:
        raise HTTPException(status_code=404, detail="Radiology order not found")

    return _radiology_response(order)


@router.put("/{order_id}", response_model=RadiologyResponse)
async def update_radiology_order(
    order_id: str,
    data: RadiologyUpdate,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'RADIOLOGIST')),
    db: Session = Depends(get_db)
):
    """Update radiology order"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    order = db_session.query(Radiology).options(
        joinedload(Radiology.patient),
        joinedload(Radiology.requester),
        joinedload(Radiology.radiologist),
    ).filter_by(id=order_id, facility_slug=facility_slug).first()
    if not order:
        raise HTTPException(status_code=404, detail="Radiology order not found")

    previous_status = order.status
    if data.status is not None:
        if data.status not in Radiology.STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(Radiology.STATUSES)}")
        order.status = data.status

    if data.radiologist_id is not None:
        radiologist = db_session.query(User).filter_by(
            id=data.radiologist_id,
            facility_slug=facility_slug,
        ).first()
        if not radiologist:
            raise HTTPException(status_code=404, detail="Radiologist not found")
        order.radiologist_id = data.radiologist_id

    if data.clinical_notes is not None:
        order.clinical_notes = Validators.sanitize_string(data.clinical_notes)

    order.save()
    db_session.commit()

    if order.status == "completed" and previous_status != "completed":
        OrderWorkflowService.record(
            facility_slug=facility_slug,
            patient_id=order.patient_id,
            order_type="radiology",
            order_id=order.id,
            event_type="radiology_report_completed",
            status=order.status,
            title="Radiology report completed",
            message=f"Radiology order completed for {order.modality} {order.body_part}.",
            actor_id=current_user.id,
            target_role="DOCTOR",
            metadata={"modality": order.modality, "body_part": order.body_part},
        )
        ClinicalWorkflowService.notify_user(
            order.requested_by,
            facility_slug,
            "info",
            "Radiology report ready",
            f"Radiology report is ready for {order.modality} {order.body_part}.",
        )
        OrderWorkflowService.record(
            facility_slug=facility_slug,
            patient_id=order.patient_id,
            order_type="radiology",
            order_id=order.id,
            event_type="doctor_notified",
            status="NOTIFIED",
            title="Doctor notified",
            message="Ordering clinician was notified that the radiology report is ready.",
            actor_id=current_user.id,
            target_role="DOCTOR",
            metadata={"requested_by": order.requested_by},
        )
        db_session.commit()

    return _radiology_response(order)


@router.put("/{order_id}/report", response_model=RadiologyResponse)
async def add_radiology_report(
    order_id: str,
    data: RadiologyReport,
    current_user: User = Depends(role_required('ADMIN', 'RADIOLOGIST')),
    db: Session = Depends(get_db)
):
    """Add or update radiology report"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    order = db_session.query(Radiology).options(
        joinedload(Radiology.patient),
        joinedload(Radiology.requester),
        joinedload(Radiology.radiologist),
    ).filter_by(id=order_id, facility_slug=facility_slug).first()
    if not order:
        raise HTTPException(status_code=404, detail="Radiology order not found")

    if not data.report:
        raise HTTPException(status_code=400, detail="Report text is required")

    order.report = Validators.sanitize_string(data.report)
    order.report_date = datetime.utcnow()
    order.status = 'completed'

    order.save()
    patient = db_session.query(Patient).filter_by(id=order.patient_id, facility_slug=facility_slug).first()
    OrderWorkflowService.record(
        facility_slug=facility_slug,
        patient_id=order.patient_id,
        order_type="radiology",
        order_id=order.id,
        event_type="radiology_report_completed",
        status=order.status,
        title="Radiology report completed",
        message=f"Radiology report completed for {order.modality} {order.body_part}.",
        actor_id=current_user.id,
        target_role="DOCTOR",
        metadata={"modality": order.modality, "body_part": order.body_part},
    )
    if patient:
        PatientNotificationService.create(
            facility_slug=facility_slug,
            patient=patient,
            notification_type="radiology_report_ready",
            title="Radiology report ready",
            message="Your radiology report is ready. Please contact your care team for review.",
            source_type="radiology",
            source_id=order.id,
            metadata={"modality": order.modality, "body_part": order.body_part},
        )
    ClinicalWorkflowService.notify_user(
        order.requested_by,
        facility_slug,
        "info",
        "Radiology report ready",
        f"Radiology report is ready for {order.modality} {order.body_part}.",
    )
    OrderWorkflowService.record(
        facility_slug=facility_slug,
        patient_id=order.patient_id,
        order_type="radiology",
        order_id=order.id,
        event_type="doctor_notified",
        status="NOTIFIED",
        title="Doctor notified",
        message="Ordering clinician was notified that the radiology report is ready.",
        actor_id=current_user.id,
        target_role="DOCTOR",
        metadata={"requested_by": order.requested_by},
    )
    db_session.commit()

    return _radiology_response(order)
