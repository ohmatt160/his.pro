from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.extensions import db_session, get_db
from app.models.patient import Patient
from app.models.user import User
from app.models.ward import WardAdmission, WardBed
from app.schemas.wards import (
    NursingObservationCreate,
    WardAdmissionCreate,
    WardAdmissionResponse,
    WardAdmissionUpdate,
    WardBedCreate,
    WardBedResponse,
    WardBedUpdate,
)
from app.services.patient_notification_service import PatientNotificationService
from app.utils.branch_scope import belongs_to_branch, user_branch_id
from app.utils.dependencies import role_required
from app.utils.validators import Validators

router = APIRouter(prefix="/wards", tags=["wards"])


def _require_facility(current_user: User) -> str:
    if not current_user.facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")
    return current_user.facility_slug


def _get_patient(patient_id: str, facility_slug: str, current_user: User | None = None) -> Patient:
    patient = db_session.query(Patient).filter_by(
        id=patient_id,
        facility_slug=facility_slug,
        is_active=True,
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    branch_id = None if not current_user or current_user.role == "ADMIN" else user_branch_id(current_user)
    if branch_id and not belongs_to_branch(patient, branch_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


def _get_bed(bed_id: str, facility_slug: str) -> WardBed:
    bed = db_session.query(WardBed).filter_by(id=bed_id, facility_slug=facility_slug).first()
    if not bed:
        raise HTTPException(status_code=404, detail="Ward bed not found")
    return bed


def _get_admission(admission_id: str, facility_slug: str) -> WardAdmission:
    admission = db_session.query(WardAdmission).filter_by(
        id=admission_id,
        facility_slug=facility_slug,
    ).first()
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")
    return admission


def _bed_response(bed: WardBed) -> WardBedResponse:
    return WardBedResponse(
        id=str(bed.id),
        facility_slug=bed.facility_slug,
        ward_name=bed.ward_name,
        bed_number=bed.bed_number,
        status=bed.status,
        notes=bed.notes,
        created_at=bed.created_at.isoformat() if bed.created_at else "",
        updated_at=bed.updated_at.isoformat() if bed.updated_at else None,
    )


def _admission_response(admission: WardAdmission) -> WardAdmissionResponse:
    patient = admission.patient
    bed = admission.bed
    return WardAdmissionResponse(
        id=str(admission.id),
        facility_slug=admission.facility_slug,
        patient_id=str(admission.patient_id),
        patient_name=patient.full_name if patient else "Unknown patient",
        patient_phone=patient.phone if patient else None,
        bed_id=str(admission.bed_id) if admission.bed_id else None,
        bed_number=bed.bed_number if bed else None,
        ward_name=admission.ward_name,
        reason=admission.reason,
        acuity=admission.acuity,
        status=admission.status,
        observations=admission.observations or [],
        nursing_notes=admission.nursing_notes or [],
        admitted_by=str(admission.admitted_by),
        admitted_at=admission.admitted_at.isoformat() if admission.admitted_at else "",
        discharged_at=admission.discharged_at.isoformat() if admission.discharged_at else None,
        created_at=admission.created_at.isoformat() if admission.created_at else "",
        updated_at=admission.updated_at.isoformat() if admission.updated_at else None,
    )


@router.get("/beds", response_model=List[WardBedResponse])
async def list_beds(
    ward_name: Optional[str] = Query(None, max_length=120),
    status_filter: Optional[str] = Query(None, alias="status", pattern="^(AVAILABLE|OCCUPIED|MAINTENANCE)$"),
    current_user: User = Depends(role_required("ADMIN", "BRANCH_ADMIN", "DOCTOR", "NURSE", "RECEPTIONIST")),
    db: Session = Depends(get_db),
):
    if current_user.role != "ADMIN" and user_branch_id(current_user):
        return []

    facility_slug = _require_facility(current_user)
    query = db_session.query(WardBed).filter_by(facility_slug=facility_slug)
    if ward_name:
        query = query.filter_by(ward_name=Validators.sanitize_string(ward_name))
    if status_filter:
        query = query.filter_by(status=status_filter)
    beds = query.order_by(WardBed.ward_name.asc(), WardBed.bed_number.asc()).all()
    return [_bed_response(bed) for bed in beds]


@router.post("/beds", response_model=WardBedResponse, status_code=status.HTTP_201_CREATED)
async def create_bed(
    data: WardBedCreate,
    current_user: User = Depends(role_required("ADMIN", "NURSE")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    ward_name = Validators.sanitize_string(data.ward_name)
    bed_number = Validators.sanitize_string(data.bed_number)

    existing = db_session.query(WardBed).filter_by(
        facility_slug=facility_slug,
        ward_name=ward_name,
        bed_number=bed_number,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ward bed already exists")

    bed = WardBed(
        facility_slug=facility_slug,
        ward_name=ward_name,
        bed_number=bed_number,
        status=data.status,
        notes=Validators.sanitize_string(data.notes) if data.notes else None,
    )
    db_session.add(bed)
    db_session.commit()
    db_session.refresh(bed)
    return _bed_response(bed)


@router.put("/beds/{bed_id}", response_model=WardBedResponse)
async def update_bed(
    bed_id: str,
    data: WardBedUpdate,
    current_user: User = Depends(role_required("ADMIN", "NURSE")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    bed = _get_bed(bed_id, facility_slug)
    payload = data.model_dump(exclude_unset=True)
    if "ward_name" in payload and payload["ward_name"] is not None:
        payload["ward_name"] = Validators.sanitize_string(payload["ward_name"])
    if "bed_number" in payload and payload["bed_number"] is not None:
        payload["bed_number"] = Validators.sanitize_string(payload["bed_number"])
    if "notes" in payload and payload["notes"] is not None:
        payload["notes"] = Validators.sanitize_string(payload["notes"])

    for key, value in payload.items():
        if value is not None:
            setattr(bed, key, value)
    db_session.add(bed)
    db_session.commit()
    db_session.refresh(bed)
    return _bed_response(bed)


@router.get("/admissions", response_model=List[WardAdmissionResponse])
async def list_admissions(
    status_filter: Optional[str] = Query(None, alias="status", pattern="^(ACTIVE|DISCHARGED|TRANSFERRED)$"),
    patient_id: Optional[str] = Query(None),
    current_user: User = Depends(role_required("ADMIN", "BRANCH_ADMIN", "DOCTOR", "NURSE")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    query = db_session.query(WardAdmission).filter_by(facility_slug=facility_slug)
    branch_id = None if current_user.role == "ADMIN" else user_branch_id(current_user)
    if branch_id:
        query = query.join(Patient, WardAdmission.patient_id == Patient.id).filter(
            Patient.facility_slug == facility_slug,
            Patient.is_active == True,
            (Patient.branch_id == branch_id) | (Patient.department_id == branch_id),
        )
    if status_filter:
        query = query.filter(WardAdmission.status == status_filter)
    if patient_id:
        _get_patient(patient_id, facility_slug, current_user)
        query = query.filter(WardAdmission.patient_id == patient_id)
    admissions = query.order_by(WardAdmission.admitted_at.desc()).limit(100).all()
    return [_admission_response(admission) for admission in admissions]


@router.post("/admissions", response_model=WardAdmissionResponse, status_code=status.HTTP_201_CREATED)
async def admit_patient(
    data: WardAdmissionCreate,
    current_user: User = Depends(role_required("ADMIN", "BRANCH_ADMIN", "DOCTOR", "NURSE")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    _get_patient(data.patient_id, facility_slug, current_user)

    existing = db_session.query(WardAdmission).filter_by(
        facility_slug=facility_slug,
        patient_id=data.patient_id,
        status="ACTIVE",
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Patient already has an active admission")

    bed = _get_bed(data.bed_id, facility_slug) if data.bed_id else None
    if bed and bed.status != "AVAILABLE":
        raise HTTPException(status_code=400, detail="Ward bed is not available")

    ward_name = Validators.sanitize_string(data.ward_name)
    admission = WardAdmission(
        facility_slug=facility_slug,
        patient_id=data.patient_id,
        bed_id=bed.id if bed else None,
        admitted_by=current_user.id,
        ward_name=ward_name,
        reason=Validators.sanitize_string(data.reason) if data.reason else None,
        acuity=data.acuity,
        status="ACTIVE",
        observations=[],
        nursing_notes=[],
    )
    if bed:
        bed.status = "OCCUPIED"
        db_session.add(bed)

    db_session.add(admission)
    db_session.commit()
    db_session.refresh(admission)
    return _admission_response(admission)


@router.put("/admissions/{admission_id}", response_model=WardAdmissionResponse)
async def update_admission(
    admission_id: str,
    data: WardAdmissionUpdate,
    current_user: User = Depends(role_required("ADMIN", "BRANCH_ADMIN", "DOCTOR", "NURSE")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    admission = _get_admission(admission_id, facility_slug)
    _get_patient(str(admission.patient_id), facility_slug, current_user)
    payload = data.model_dump(exclude_unset=True)

    if "bed_id" in payload:
        new_bed = _get_bed(payload["bed_id"], facility_slug) if payload["bed_id"] else None
        if new_bed and new_bed.status != "AVAILABLE" and new_bed.id != admission.bed_id:
            raise HTTPException(status_code=400, detail="Ward bed is not available")
        if admission.bed_id and admission.bed_id != (new_bed.id if new_bed else None):
            old_bed = _get_bed(admission.bed_id, facility_slug)
            old_bed.status = "AVAILABLE"
            db_session.add(old_bed)
        if new_bed:
            new_bed.status = "OCCUPIED"
            db_session.add(new_bed)
        admission.bed_id = new_bed.id if new_bed else None
        payload.pop("bed_id")

    if "ward_name" in payload and payload["ward_name"] is not None:
        payload["ward_name"] = Validators.sanitize_string(payload["ward_name"])
    if "reason" in payload and payload["reason"] is not None:
        payload["reason"] = Validators.sanitize_string(payload["reason"])

    for key, value in payload.items():
        if value is not None:
            setattr(admission, key, value)
    db_session.add(admission)
    db_session.commit()
    db_session.refresh(admission)
    return _admission_response(admission)


@router.post("/admissions/{admission_id}/observations", response_model=WardAdmissionResponse)
async def add_observation(
    admission_id: str,
    data: NursingObservationCreate,
    current_user: User = Depends(role_required("ADMIN", "BRANCH_ADMIN", "DOCTOR", "NURSE")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    admission = _get_admission(admission_id, facility_slug)
    _get_patient(str(admission.patient_id), facility_slug, current_user)
    if admission.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Cannot update a closed admission")

    entry = {
        "created_at": datetime.utcnow().isoformat(),
        "created_by": str(current_user.id),
        "vital_signs": data.vital_signs or {},
        "note": Validators.sanitize_string(data.note) if data.note else None,
        "medication_round": Validators.sanitize_string(data.medication_round) if data.medication_round else None,
    }
    observations = list(admission.observations or [])
    notes = list(admission.nursing_notes or [])
    observations.append(entry)
    if entry["note"] or entry["medication_round"]:
        notes.append(entry)
    admission.observations = observations
    admission.nursing_notes = notes
    db_session.add(admission)
    db_session.commit()
    db_session.refresh(admission)
    return _admission_response(admission)


@router.post("/admissions/{admission_id}/discharge", response_model=WardAdmissionResponse)
async def discharge_patient(
    admission_id: str,
    current_user: User = Depends(role_required("ADMIN", "BRANCH_ADMIN", "DOCTOR", "NURSE")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    admission = _get_admission(admission_id, facility_slug)
    _get_patient(str(admission.patient_id), facility_slug, current_user)
    if admission.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Admission is already closed")

    admission.status = "DISCHARGED"
    admission.discharged_at = datetime.utcnow()
    if admission.bed_id:
        bed = _get_bed(admission.bed_id, facility_slug)
        bed.status = "AVAILABLE"
        db_session.add(bed)
    db_session.add(admission)
    patient = admission.patient or _get_patient(admission.patient_id, facility_slug, current_user)
    PatientNotificationService.create(
        facility_slug=facility_slug,
        patient=patient,
        notification_type="discharge_follow_up",
        title="Discharge follow-up",
        message="You have been discharged. Please follow your care instructions and contact the hospital if symptoms worsen.",
        source_type="ward_admission",
        source_id=admission.id,
        metadata={"ward_name": admission.ward_name, "discharged_at": admission.discharged_at.isoformat()},
    )
    db_session.commit()
    db_session.refresh(admission)
    return _admission_response(admission)
