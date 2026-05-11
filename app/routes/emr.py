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
from app.services.medical_record_service import MedicalRecordService
from app.utils.dependencies import get_current_user, role_required
from app.models.user import User
from app.models.patient import Patient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/emr", tags=["emr"])


class MedicalRecordCreate(BaseModel):
    patient_id: str = Field(...)
    record_type: str = Field(..., pattern="^(CONSULTATION|LAB_RESULT|IMAGING|PRESCRIPTION|PROCEDURE|NOTE|VACCINATION)$")
    title: str = Field(..., max_length=200)
    description: Optional[str] = Field(None)
    data: Optional[dict] = Field(default_factory=dict)
    attachments: Optional[List[str]] = Field(default_factory=list)


class MedicalRecordUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None)
    data: Optional[dict] = None
    attachments: Optional[List[str]] = None


class MedicalRecordResponse(BaseModel):
    id: str
    patient_id: str
    record_type: str
    title: str
    description: Optional[str]
    data: Optional[dict]
    attachments: Optional[List[str]]
    created_by: str
    facility_slug: Optional[str]
    created_at: str
    updated_at: Optional[str]


class MessageResponse(BaseModel):
    message: str


@router.get("", response_model=List[MedicalRecordResponse])
async def get_records(
    patient_id: Optional[str] = Query(None),
    record_type: Optional[str] = Query(None, pattern="^(CONSULTATION|LAB_RESULT|IMAGING|PRESCRIPTION|PROCEDURE|NOTE|VACCINATION)$"),
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
            raise HTTPException(status_code=404, detail="Patient not found")
        records = MedicalRecordService.get_records_by_patient(patient_id, facility_slug, record_type)
    else:
        records = MedicalRecordService.get_all_records(facility_slug, record_type)

    return [
        MedicalRecordResponse(
            id=str(r.id),
            patient_id=str(r.patient_id),
            record_type=r.record_type,
            title=r.title,
            description=r.description,
            data=r.data,
            attachments=r.attachments,
            created_by=str(r.created_by),
            facility_slug=r.facility_slug,
            created_at=r.created_at.isoformat() if r.created_at else "",
            updated_at=r.updated_at.isoformat() if r.updated_at else None
        ) for r in records
    ]


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

    record = MedicalRecordService.create_record(data.dict(), current_user.id, facility_slug)

    return MedicalRecordResponse(
        id=str(record.id),
        patient_id=str(record.patient_id),
        record_type=record.record_type,
        title=record.title,
        description=record.description,
        data=record.data,
        attachments=record.attachments,
        created_by=str(record.created_by),
        facility_slug=record.facility_slug,
        created_at=record.created_at.isoformat() if record.created_at else "",
        updated_at=record.updated_at.isoformat() if record.updated_at else None
    )


@router.get("/{record_id}", response_model=MedicalRecordResponse)
async def get_record(
    record_id: str,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    record = MedicalRecordService.get_record_by_id(record_id)

    if not record or record.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Medical record not found")

    return MedicalRecordResponse(
        id=str(record.id),
        patient_id=str(record.patient_id),
        record_type=record.record_type,
        title=record.title,
        description=record.description,
        data=record.data,
        attachments=record.attachments,
        created_by=str(record.created_by),
        facility_slug=record.facility_slug,
        created_at=record.created_at.isoformat() if record.created_at else "",
        updated_at=record.updated_at.isoformat() if record.updated_at else None
    )


@router.put("/{record_id}", response_model=MedicalRecordResponse)
async def update_record(
    record_id: str,
    data: MedicalRecordUpdate,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    record = MedicalRecordService.get_record_by_id(record_id)

    if not record or record.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Medical record not found")

    updated_record = MedicalRecordService.update_record(record, data.dict(exclude_unset=True))

    return MedicalRecordResponse(
        id=str(updated_record.id),
        patient_id=str(updated_record.patient_id),
        record_type=updated_record.record_type,
        title=updated_record.title,
        description=updated_record.description,
        data=updated_record.data,
        attachments=updated_record.attachments,
        created_by=str(updated_record.created_by),
        facility_slug=updated_record.facility_slug,
        created_at=updated_record.created_at.isoformat() if updated_record.created_at else "",
        updated_at=updated_record.updated_at.isoformat() if updated_record.updated_at else None
    )


@router.delete("/{record_id}", response_model=MessageResponse)
async def delete_record(
    record_id: str,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    record = MedicalRecordService.get_record_by_id(record_id)

    if not record or record.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Medical record not found")

    MedicalRecordService.delete_record(record)

    return MessageResponse(message="Medical record deleted successfully")
