"""
Radiology Routes - FastAPI Version
Converted from Flask-RESTx radiology_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging

from app.extensions import get_db, db_session
from app.utils.dependencies import get_current_user, role_required
from app.utils.validators import Validators
from app.models.user import User
from app.models.patient import Patient
from app.models.radiology import Radiology

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/radiology", tags=["radiology"])


class RadiologyCreate(BaseModel):
    patient_id: str = Field(...)
    facility_slug: str = Field(...)
    modality: str = Field(..., pattern="^(X-ray|CT|MRI|Ultrasound)$")
    body_part: str = Field(..., max_length=100)
    clinical_notes: Optional[str] = Field(None)


class RadiologyUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(pending|ordered|completed|cancelled)$")
    radiologist_id: Optional[str] = Field(None)
    clinical_notes: Optional[str] = Field(None)


class RadiologyReport(BaseModel):
    report: str = Field(...)


class RadiologyResponse(BaseModel):
    id: str
    patient_id: str
    facility_slug: str
    modality: str
    body_part: str
    clinical_notes: Optional[str]
    status: str
    requested_by: str
    radiologist_id: Optional[str]
    report: Optional[str]
    report_date: Optional[str]
    request_date: str
    patient_name: Optional[str]
    requested_by_name: Optional[str]
    radiologist_name: Optional[str]


class MessageResponse(BaseModel):
    message: str


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
    query = db_session.query(Radiology)

    # Filter by facility if not admin
    if current_user.role != 'ADMIN' and current_user.facility_slug:
        query = query.filter_by(facility_slug=current_user.facility_slug)
    elif facility_slug:
        query = query.filter_by(facility_slug=facility_slug)

    if status:
        query = query.filter_by(status=status)
    if patient_id:
        query = query.filter_by(patient_id=patient_id)

    query = query.order_by(Radiology.request_date.desc())

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page

    result = []
    for order in items:
        # Compute full names
        patient_name = None
        if order.patient:
            fname = order.patient.first_name or ''
            lname = order.patient.last_name or ''
            patient_name = (fname + ' ' + lname).strip() or None

        requester_name = None
        if order.requester:
            rfname = order.requester.first_name or ''
            rlname = order.requester.last_name or ''
            requester_name = (rfname + ' ' + rlname).strip() or None

        radiologist_name = None
        if order.radiologist:
            ra_fname = order.radiologist.first_name or ''
            ra_lname = order.radiologist.last_name or ''
            radiologist_name = (ra_fname + ' ' + ra_lname).strip() or None

        result.append(RadiologyResponse(
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
            patient_name=patient_name,
            requested_by_name=requester_name,
            radiologist_name=radiologist_name
        ))

    return result


@router.post("", response_model=RadiologyResponse, status_code=status.HTTP_201_CREATED)
async def create_radiology_order(
    data: RadiologyCreate,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR')),
    db: Session = Depends(get_db)
):
    """Create a new radiology order"""
    # Validate required fields
    if not data.patient_id or not data.facility_slug or not data.modality or not data.body_part:
        raise HTTPException(status_code=400, detail="Missing required fields")

    # Validate patient exists and belongs to facility
    patient = db_session.query(Patient).filter_by(id=data.patient_id, facility_slug=data.facility_slug).first()
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
        facility_slug=data.facility_slug,
        modality=data.modality,
        body_part=data.body_part,
        clinical_notes=clinical_notes,
        requested_by=current_user.id,
        status='pending'
    )
    db_session.add(radiology)
    db_session.commit()
    db_session.refresh(radiology)

    # Compute names for response
    requester_name = f"{current_user.first_name} {current_user.last_name}".strip() if current_user.first_name or current_user.last_name else None

    return RadiologyResponse(
        id=str(radiology.id),
        patient_id=str(radiology.patient_id),
        facility_slug=radiology.facility_slug,
        modality=radiology.modality,
        body_part=radiology.body_part,
        clinical_notes=radiology.clinical_notes,
        status=radiology.status,
        requested_by=str(radiology.requested_by),
        radiologist_id=None,
        report=None,
        report_date=None,
        request_date=radiology.request_date.isoformat() if radiology.request_date else "",
        patient_name=None,  # could load patient but not needed
        requested_by_name=requester_name,
        radiologist_name=None
    )


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

    order = db_session.query(Radiology).filter_by(id=order_id, facility_slug=facility_slug).first()
    if not order:
        raise HTTPException(status_code=404, detail="Radiology order not found")

    # Compute names
    patient_name = f"{order.patient.first_name} {order.patient.last_name}".strip() if order.patient else None
    requester_name = f"{order.requester.first_name} {order.requester.last_name}".strip() if order.requester else None
    radiologist_name = f"{order.radiologist.first_name} {order.radiologist.last_name}".strip() if order.radiologist else None

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
        patient_name=patient_name,
        requested_by_name=requester_name,
        radiologist_name=radiologist_name
    )


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

    order = db_session.query(Radiology).filter_by(id=order_id, facility_slug=facility_slug).first()
    if not order:
        raise HTTPException(status_code=404, detail="Radiology order not found")

    if data.status is not None:
        if data.status not in Radiology.STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(Radiology.STATUSES)}")
        order.status = data.status

    if data.radiologist_id is not None:
        radiologist = db_session.query(User).filter_by(id=data.radiologist_id).first()
        if not radiologist:
            raise HTTPException(status_code=404, detail="Radiologist not found")
        order.radiologist_id = data.radiologist_id

    if data.clinical_notes is not None:
        order.clinical_notes = Validators.sanitize_string(data.clinical_notes)

    order.save()
    db_session.commit()

    # Compute names
    patient_name = f"{order.patient.first_name} {order.patient.last_name}".strip() if order.patient else None
    requester_name = f"{order.requester.first_name} {order.requester.last_name}".strip() if order.requester else None
    radiologist_name = f"{order.radiologist.first_name} {order.radiologist.last_name}".strip() if order.radiologist else None

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
        patient_name=patient_name,
        requested_by_name=requester_name,
        radiologist_name=radiologist_name
    )


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

    order = db_session.query(Radiology).filter_by(id=order_id, facility_slug=facility_slug).first()
    if not order:
        raise HTTPException(status_code=404, detail="Radiology order not found")

    if not data.report:
        raise HTTPException(status_code=400, detail="Report text is required")

    order.report = Validators.sanitize_string(data.report)
    order.report_date = datetime.utcnow()

    # Update status to completed if not already
    if order.status == 'ordered':
        order.status = 'completed'

    order.save()
    db_session.commit()

    # Compute names
    patient_name = f"{order.patient.first_name} {order.patient.last_name}".strip() if order.patient else None
    requester_name = f"{order.requester.first_name} {order.requester.last_name}".strip() if order.requester else None
    radiologist_name = f"{order.radiologist.first_name} {order.radiologist.last_name}".strip() if order.radiologist else None

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
        patient_name=patient_name,
        requested_by_name=requester_name,
        radiologist_name=radiologist_name
    )
