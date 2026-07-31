"""
Radiology Routes - FastAPI Version
Converted from Flask-RESTx radiology_resource.py
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
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
from app.services.realtime_service import publish_tenant_event
from app.services.write_idempotency_service import WriteIdempotencyService
from app.utils.dependencies import get_current_user, role_required
from app.utils.branch_scope import ensure_patient_branch_access, require_facility_slug, require_tenant_row, tenant_query
from app.utils.validators import Validators
from app.utils.idempotency import IdempotencyConflictError
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
        department_id=order.department_id,
        branch_id=order.branch_id or order.department_id,
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


def _publish_radiology_event(event_type: str, order: Radiology) -> None:
    publish_tenant_event(
        event_type=event_type,
        facility_slug=order.facility_slug,
        branch_id=order.branch_id or order.department_id,
        roles=["ADMIN", "BRANCH_ADMIN", "DOCTOR", "NURSE", "RADIOLOGIST"],
        modules=["radiology", "consultations", "records"],
        resource_id=order.id,
        payload={"patient_id": order.patient_id, "status": order.status},
    )


@router.get("", response_model=List[RadiologyResponse])
async def get_radiology_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    facility_slug: Optional[str] = Query(None),
    status: Optional[str] = Query(None, pattern="^(pending|ordered|completed|cancelled)$"),
    patient_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None, max_length=36),
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE', 'RADIOLOGIST')),
    db: Session = Depends(get_db)
):
    """Paginated list of radiology orders"""
    facility_slug = require_facility_slug(current_user)
    query = tenant_query(db_session, Radiology, current_user, branch_id).options(
        joinedload(Radiology.patient),
        joinedload(Radiology.requester),
        joinedload(Radiology.radiologist),
    )

    if status:
        query = query.filter_by(status=status)
    if patient_id:
        patient = db_session.query(Patient).filter_by(
            id=patient_id,
            facility_slug=facility_slug,
        ).first()
        if not patient:
            return []
        ensure_patient_branch_access(patient, current_user, branch_id)
        query = query.filter_by(patient_id=patient_id)

    query = query.order_by(Radiology.request_date.desc())

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page

    return [_radiology_response(order) for order in items]


@router.post("", response_model=RadiologyResponse, status_code=status.HTTP_201_CREATED)
async def create_radiology_order(
    data: RadiologyCreate,
    response: Response,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR')),
    db: Session = Depends(get_db)
):
    """Create a new radiology order"""
    facility_slug = require_facility_slug(current_user)

    if not data.patient_id or not data.modality or not data.body_part:
        raise HTTPException(status_code=400, detail="Missing required fields")

    patient = db_session.query(Patient).filter_by(id=data.patient_id, facility_slug=facility_slug).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    branch_id = ensure_patient_branch_access(patient, current_user, data.branch_id or data.department_id)

    # Validate modality
    Radiology.MODALITIES
    if data.modality not in Radiology.MODALITIES:
        raise HTTPException(status_code=400, detail=f"Invalid modality. Must be one of: {', '.join(Radiology.MODALITIES)}")

    try:
        claim = WriteIdempotencyService.claim(
            facility_slug=facility_slug,
            facility_id=current_user.facility_id,
            actor_id=current_user.id,
            operation="radiology.order.create",
            idempotency_key=idempotency_key,
            payload={
                **data.model_dump(),
                "resolved_branch_id": branch_id or patient.branch_id or patient.department_id,
            },
        )
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    if claim.replay:
        radiology = (
            db_session.query(Radiology)
            .options(
                joinedload(Radiology.patient),
                joinedload(Radiology.requester),
                joinedload(Radiology.radiologist),
            )
            .filter_by(id=claim.record.resource_id)
            .first()
        )
        require_tenant_row(radiology, current_user, "Radiology order not found")
        response.status_code = status.HTTP_200_OK
        return _radiology_response(radiology)

    # Sanitize notes
    clinical_notes = Validators.sanitize_string(data.clinical_notes or '')

    radiology = Radiology(
        patient_id=data.patient_id,
        facility_slug=facility_slug,
        branch_id=branch_id or patient.branch_id or patient.department_id,
        department_id=branch_id or patient.department_id,
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
    WriteIdempotencyService.complete(
        claim.record,
        resource_type="radiology_order",
        resource_id=radiology.id,
        response_status=status.HTTP_201_CREATED,
    )
    db_session.commit()
    db_session.refresh(radiology)
    _publish_radiology_event("radiology.order_created", radiology)

    radiology.patient = patient
    radiology.requester = current_user
    return _radiology_response(radiology)


@router.get("/{order_id}", response_model=RadiologyResponse)
async def get_radiology_order(
    order_id: str,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE', 'RADIOLOGIST')),
    db: Session = Depends(get_db)
):
    """Get radiology order by ID"""
    order = db_session.query(Radiology).options(
        joinedload(Radiology.patient),
        joinedload(Radiology.requester),
        joinedload(Radiology.radiologist),
    ).filter_by(id=order_id).first()
    require_tenant_row(order, current_user, "Radiology order not found")

    return _radiology_response(order)


@router.put("/{order_id}", response_model=RadiologyResponse)
async def update_radiology_order(
    order_id: str,
    data: RadiologyUpdate,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'RADIOLOGIST')),
    db: Session = Depends(get_db)
):
    """Update radiology order"""
    facility_slug = require_facility_slug(current_user)

    order = db_session.query(Radiology).options(
        joinedload(Radiology.patient),
        joinedload(Radiology.requester),
        joinedload(Radiology.radiologist),
    ).filter_by(id=order_id).first()
    require_tenant_row(order, current_user, "Radiology order not found")

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
    _publish_radiology_event("radiology.order_updated", order)

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
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'RADIOLOGIST')),
    db: Session = Depends(get_db)
):
    """Add or update radiology report"""
    facility_slug = require_facility_slug(current_user)

    order = db_session.query(Radiology).options(
        joinedload(Radiology.patient),
        joinedload(Radiology.requester),
        joinedload(Radiology.radiologist),
    ).filter_by(id=order_id).first()
    require_tenant_row(order, current_user, "Radiology order not found")

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
    _publish_radiology_event("radiology.report_updated", order)

    return _radiology_response(order)
