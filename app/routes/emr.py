"""
Medical Records Routes - FastAPI Version
Converted from Flask-RESTx medical_record_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from app.extensions import get_db
from app.schemas.emr import MedicalRecordResponse, MedicalRecordCreate, MedicalRecordUpdate
from app.schemas.users import MessageResponse
from app.services.medical_record_service import MedicalRecordService
from app.utils.dependencies import get_current_user, role_required
from app.utils.branch_scope import belongs_to_branch, user_branch_id
from app.models.user import User
from app.models.patient import Patient

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




@router.get("", response_model=List[MedicalRecordResponse])
async def get_records(
    patient_id: Optional[str] = Query(None),
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    if patient_id:
        # Verify patient belongs to facility
        patient = db.query(Patient).filter_by(id=patient_id, facility_slug=facility_slug).first()
        if not _patient_accessible(patient, current_user):
            return []
        records = MedicalRecordService.get_medical_records_by_patient(patient_id, facility_slug)
    else:
        records = [
            record
            for record in MedicalRecordService.get_medical_records_by_facility(facility_slug)
            if _record_accessible(record, current_user, db)
        ]

    return [_record_response(record) for record in records]


@router.post("", response_model=MedicalRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_record(
    data: MedicalRecordCreate,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    # Verify patient belongs to facility
    patient = db.query(Patient).filter_by(id=data.patient_id, facility_slug=facility_slug).first()
    if not _patient_accessible(patient, current_user):
        raise HTTPException(status_code=404, detail="Patient not found")

    record = MedicalRecordService.create_medical_record(
        data.model_dump(),
        current_user.id,
        facility_slug,
    )

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

    updated_record = MedicalRecordService.update_medical_record(record, data.model_dump(exclude_unset=True))

    return _record_response(updated_record)


@router.delete("/{record_id}", response_model=MessageResponse)
async def delete_record(
    record_id: str,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    record = MedicalRecordService.get_medical_record_by_id(record_id)

    if not _record_accessible(record, current_user, db):
        raise HTTPException(status_code=404, detail="Medical record not found")

    MedicalRecordService.delete_medical_record(record)

    return MessageResponse(message="Medical record deleted successfully")
