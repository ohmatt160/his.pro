"""
EMR Routes - FastAPI Version
Converted from Flask-RESTx emr_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from app.extensions import get_db
from app.utils.dependencies import get_current_user, role_required
from app.services.medical_record_service import MedicalRecordService
from app.models.user import User
from app.models.patient import Patient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/emr", tags=["emr"])


# Pydantic Models
class MedicalRecordCreate(BaseModel):
    patient_id: str = Field(...)
    appointment_id: Optional[str] = Field(None)
    chief_complaint: Optional[str] = Field(None)
    vital_signs: Optional[Dict[str, Any]] = Field(None)
    symptoms: Optional[List[str]] = Field(None)
    diagnosis: Optional[List[str]] = Field(None)
    treatment_plan: Optional[str] = Field(None)
    prescriptions: Optional[List[Dict[str, Any]]] = Field(None)
    lab_orders: Optional[List[Dict[str, Any]]] = Field(None)
    follow_up_date: Optional[str] = Field(None)
    notes: Optional[str] = Field(None)


class MedicalRecordUpdate(BaseModel):
    chief_complaint: Optional[str] = Field(None)
    vital_signs: Optional[Dict[str, Any]] = Field(None)
    symptoms: Optional[List[str]] = Field(None)
    diagnosis: Optional[List[str]] = Field(None)
    treatment_plan: Optional[str] = Field(None)
    prescriptions: Optional[List[Dict[str, Any]]] = Field(None)
    lab_orders: Optional[List[Dict[str, Any]]] = Field(None)
    follow_up_date: Optional[str] = Field(None)
    notes: Optional[str] = Field(None)


class MedicalRecordResponse(BaseModel):
    id: str
    patient_id: str
    appointment_id: Optional[str]
    facility_slug: str
    chief_complaint: Optional[str]
    vital_signs: Optional[Dict[str, Any]]
    symptoms: Optional[List[str]]
    diagnosis: Optional[List[str]]
    treatment_plan: Optional[str]
    prescriptions: Optional[List[Dict[str, Any]]]
    lab_orders: Optional[List[Dict[str, Any]]]
    follow_up_date: Optional[str]
    notes: Optional[str]
    created_by: str
    created_at: str
    updated_at: Optional[str]


class ClinicalNoteCreate(BaseModel):
    patient_id: str = Field(...)
    record_id: Optional[str] = Field(None)
    note_type: Optional[str] = Field(None)
    title: Optional[str] = Field(None)
    content: str = Field(..., min_length=1)
    is_confidential: Optional[bool] = Field(False)


class ClinicalNoteUpdate(BaseModel):
    note_type: Optional[str] = Field(None)
    title: Optional[str] = Field(None)
    content: Optional[str] = Field(None)
    is_confidential: Optional[bool] = Field(None)


class ClinicalNoteResponse(BaseModel):
    id: str
    patient_id: str
    record_id: Optional[str]
    facility_slug: str
    note_type: Optional[str]
    title: Optional[str]
    content: str
    is_confidential: bool
    created_by: str
    created_at: str
    updated_at: Optional[str]


class MessageResponse(BaseModel):
    message: str


# Helper to check facility access
def check_facility_access(current_user: User):
    if not current_user.facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")
    return current_user.facility_slug


def verify_patient_access(db: Session, patient_id: str, facility_slug: str):
    patient = db.query(Patient).filter_by(id=patient_id, facility_slug=facility_slug).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


# ==================== Medical Records ====================

@router.get("/records", response_model=List[MedicalRecordResponse])
async def list_medical_records(
        patient_id: str = Query(...),
        current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE')),
        db: Session = Depends(get_db)
):
    """Get medical records for a patient"""
    facility_slug = check_facility_access(current_user)
    verify_patient_access(db, patient_id, facility_slug)

    records = MedicalRecordService.get_medical_records_by_patient(patient_id, facility_slug)
    return records


@router.post("/records", response_model=MedicalRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_medical_record(
        data: MedicalRecordCreate,
        current_user: User = Depends(role_required('ADMIN', 'DOCTOR')),
        db: Session = Depends(get_db)
):
    """Create a new medical record"""
    facility_slug = check_facility_access(current_user)
    verify_patient_access(db, data.patient_id, facility_slug)

    record_data = data.dict()
    record_data['facility_slug'] = facility_slug

    record = MedicalRecordService.create_medical_record(record_data, str(current_user.id))
    return record


@router.get("/records/{record_id}", response_model=MedicalRecordResponse)
async def get_medical_record(
        record_id: str,
        current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE')),
        db: Session = Depends(get_db)
):
    """Get medical record by ID"""
    facility_slug = check_facility_access(current_user)

    record = MedicalRecordService.get_medical_record_by_id(record_id)

    if not record or record.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Medical record not found")

    return record


@router.put("/records/{record_id}", response_model=MedicalRecordResponse)
async def update_medical_record(
        record_id: str,
        data: MedicalRecordUpdate,
        current_user: User = Depends(role_required('ADMIN', 'DOCTOR')),
        db: Session = Depends(get_db)
):
    """Update medical record"""
    facility_slug = check_facility_access(current_user)

    record = MedicalRecordService.get_medical_record_by_id(record_id)

    if not record or record.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Medical record not found")

    updated_record = MedicalRecordService.update_medical_record(record, data.dict(exclude_unset=True))
    return updated_record


# ==================== Clinical Notes ====================

@router.get("/notes", response_model=List[ClinicalNoteResponse])
async def list_clinical_notes(
        patient_id: str = Query(...),
        current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE')),
        db: Session = Depends(get_db)
):
    """Get clinical notes for a patient"""
    facility_slug = check_facility_access(current_user)
    verify_patient_access(db, patient_id, facility_slug)

    notes = MedicalRecordService.get_clinical_notes_by_patient(patient_id, facility_slug)
    return notes


@router.post("/notes", response_model=ClinicalNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_clinical_note(
        data: ClinicalNoteCreate,
        current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE')),
        db: Session = Depends(get_db)
):
    """Create a new clinical note"""
    facility_slug = check_facility_access(current_user)
    verify_patient_access(db, data.patient_id, facility_slug)

    note_data = data.dict()
    note_data['facility_slug'] = facility_slug

    note = MedicalRecordService.create_clinical_note(note_data, str(current_user.id))
    return note


@router.get("/notes/{note_id}", response_model=ClinicalNoteResponse)
async def get_clinical_note(
        note_id: str,
        current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE')),
        db: Session = Depends(get_db)
):
    """Get clinical note by ID"""
    facility_slug = check_facility_access(current_user)

    note = MedicalRecordService.get_clinical_note_by_id(note_id)

    if not note or note.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Clinical note not found")

    return note


@router.put("/notes/{note_id}", response_model=ClinicalNoteResponse)
async def update_clinical_note(
        note_id: str,
        data: ClinicalNoteUpdate,
        current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE')),
        db: Session = Depends(get_db)
):
    """Update clinical note"""
    facility_slug = check_facility_access(current_user)

    note = MedicalRecordService.get_clinical_note_by_id(note_id)

    if not note or note.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Clinical note not found")

    updated_note = MedicalRecordService.update_clinical_note(note, data.dict(exclude_unset=True))
    return updated_note