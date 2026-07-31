"""
Medical Records Routes - FastAPI Version
Converted from Flask-RESTx medical_record_resource.py
"""

from fastapi import APIRouter, Depends, Header, HTTPException, status, Query, Request, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from app.extensions import get_db
from app.schemas.emr import MedicalRecordResponse, MedicalRecordCreate, MedicalRecordUpdate
from app.schemas.users import MessageResponse
from app.services.medical_record_service import MedicalRecordService
from app.services.audit_log_service import AuditLogService
from app.services.realtime_service import publish_tenant_event
from app.utils.dependencies import get_current_user, role_required
from app.utils.branch_scope import belongs_to_branch, user_branch_id
from app.models.user import User
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.utils.idempotency import (
    IdempotencyConflictError,
    idempotency_payload_hash,
    require_idempotency_key,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/emr", tags=["emr"])


def _record_response(record) -> MedicalRecordResponse:
    return MedicalRecordResponse(
        id=str(record.id),
        patient_id=str(record.patient_id),
        appointment_id=str(record.appointment_id) if record.appointment_id else None,
        chief_complaint=record.chief_complaint,
        vital_signs=record.vital_signs or {},
        symptoms=record.symptoms or [],
        diagnosis=record.diagnosis or [],
        treatment_plan=record.treatment_plan,
        prescriptions=record.prescriptions or [],
        lab_orders=record.lab_orders or [],
        follow_up_date=record.follow_up_date.isoformat() if record.follow_up_date else None,
        notes=record.notes,
        status=record.status or "ACTIVE",
        void_reason=record.void_reason,
        voided_at=record.voided_at.isoformat() if record.voided_at else None,
        voided_by=str(record.voided_by) if record.voided_by else None,
        created_by=str(record.created_by),
        facility_slug=record.facility_slug,
        created_at=record.created_at.isoformat() if record.created_at else "",
        updated_at=record.updated_at.isoformat() if record.updated_at else None
    )


def _patient_accessible(patient: Patient | None, current_user: User) -> bool:
    if not patient:
        return False
    branch_id = None if current_user.role == "ADMIN" else user_branch_id(current_user)
    return belongs_to_branch(patient, branch_id)


def _record_accessible(record, current_user: User, db: Session) -> bool:
    if not record or record.facility_slug != current_user.facility_slug:
        return False
    if current_user.role == "ADMIN":
        return True
    patient = db.query(Patient).filter_by(id=record.patient_id, facility_slug=current_user.facility_slug).first()
    return _patient_accessible(patient, current_user)


def _publish_record_event(event_type: str, record, patient: Patient | None = None) -> None:
    publish_tenant_event(
        event_type=event_type,
        facility_slug=record.facility_slug,
        branch_id=(patient.branch_id or patient.department_id) if patient else None,
        roles=["ADMIN", "BRANCH_ADMIN", "DOCTOR", "NURSE"],
        modules=["records", "consultations"],
        resource_id=record.id,
        payload={"patient_id": record.patient_id},
    )




@router.get("", response_model=List[MedicalRecordResponse])
async def get_records(
    patient_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    query = (
        db.query(MedicalRecord)
        .join(Patient, Patient.id == MedicalRecord.patient_id)
        .filter(
            MedicalRecord.facility_slug == facility_slug,
            Patient.facility_slug == facility_slug,
        )
    )
    if patient_id:
        query = query.filter(MedicalRecord.patient_id == patient_id)
    if current_user.role != "ADMIN":
        branch_id = user_branch_id(current_user)
        if branch_id:
            query = query.filter(
                or_(
                    Patient.branch_id == branch_id,
                    Patient.department_id == branch_id,
                )
            )

    records = (
        query.order_by(MedicalRecord.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return [_record_response(record) for record in records]


@router.post("", response_model=MedicalRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_record(
    data: MedicalRecordCreate,
    response: Response,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")
    idempotency_key = require_idempotency_key(idempotency_key)

    # Verify patient belongs to facility
    patient = db.query(Patient).filter_by(id=data.patient_id, facility_slug=facility_slug).first()
    if not _patient_accessible(patient, current_user):
        raise HTTPException(status_code=404, detail="Patient not found")

    payload = data.model_dump()
    try:
        record, created = MedicalRecordService.create_medical_record(
            payload,
            current_user.id,
            facility_slug,
            current_user.facility_id,
            idempotency_key=idempotency_key,
            payload_hash=idempotency_payload_hash({
                "facility_slug": facility_slug,
                "record": payload,
            }),
        )
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if created:
        _publish_record_event("record.created", record, patient)
    else:
        response.status_code = status.HTTP_200_OK

    return _record_response(record)


@router.get("/{record_id}", response_model=MedicalRecordResponse)
async def get_record(
    record_id: str,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    record = MedicalRecordService.get_medical_record_by_id(record_id)

    if not _record_accessible(record, current_user, db):
        raise HTTPException(status_code=404, detail="Medical record not found")

    return _record_response(record)


@router.put("/{record_id}", response_model=MedicalRecordResponse)
async def update_record(
    record_id: str,
    data: MedicalRecordUpdate,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    record = MedicalRecordService.get_medical_record_by_id(record_id)

    if not _record_accessible(record, current_user, db):
        raise HTTPException(status_code=404, detail="Medical record not found")

    try:
        updated_record = MedicalRecordService.update_medical_record(
            record,
            data.model_dump(exclude_unset=True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    patient = db.query(Patient).filter_by(id=updated_record.patient_id, facility_slug=facility_slug).first()
    _publish_record_event("record.updated", updated_record, patient)

    return _record_response(updated_record)


@router.delete("/{record_id}", response_model=MessageResponse)
async def delete_record(
    record_id: str,
    request: Request,
    reason: str = Query(
        "Voided by an authorized administrator",
        min_length=5,
        max_length=500,
    ),
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    record = MedicalRecordService.get_medical_record_by_id(record_id)

    if not _record_accessible(record, current_user, db):
        raise HTTPException(status_code=404, detail="Medical record not found")

    patient = db.query(Patient).filter_by(id=record.patient_id, facility_slug=facility_slug).first()
    record, changed = MedicalRecordService.void_medical_record(
        record,
        reason=reason,
        voided_by=current_user.id,
    )
    if changed:
        _publish_record_event("record.voided", record, patient)
        AuditLogService.log_action(
            user_id=current_user.id,
            action="VOID_MEDICAL_RECORD",
            resource_type="medical_record",
            resource_id=record.id,
            facility_slug=facility_slug,
            details={"reason": reason, "patient_id": record.patient_id},
            request=request,
        )

    return MessageResponse(message="Medical record voided and retained for audit")
