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




@router.get("", response_model=List[MedicalRecordResponse])
async def get_records(
    patient_id: Optional[str] = Query(None),
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    if patient_id:
        # Verify patient belongs to facility
        patient = db.query(Patient).filter_by(id=patient_id, facility_slug=facility_slug).first()
        if not patient:
            return []
        records = MedicalRecordService.get_medical_records_by_patient(patient_id, facility_slug)
    else:
        records = MedicalRecordService.get_medical_records_by_facility(facility_slug)

    return [_record_response(record) for record in records]


@router.post("", response_model=MedicalRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_record(
    data: MedicalRecordCreate,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    # Verify patient belongs to facility
    patient = db.query(Patient).filter_by(id=data.patient_id, facility_slug=facility_slug).first()
    if not patient:
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
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    record = MedicalRecordService.get_medical_record_by_id(record_id)

    if not record or record.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Medical record not found")

    return _record_response(record)


@router.put("/{record_id}", response_model=MedicalRecordResponse)
async def update_record(
    record_id: str,
    data: MedicalRecordUpdate,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    record = MedicalRecordService.get_medical_record_by_id(record_id)

    if not record or record.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Medical record not found")

    updated_record = MedicalRecordService.update_medical_record(record, data.model_dump(exclude_unset=True))

    return _record_response(updated_record)


@router.delete("/{record_id}", response_model=MessageResponse)
async def delete_record(
    record_id: str,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    record = MedicalRecordService.get_medical_record_by_id(record_id)

    if not record or record.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Medical record not found")

    MedicalRecordService.delete_medical_record(record)

    return MessageResponse(message="Medical record deleted successfully")
