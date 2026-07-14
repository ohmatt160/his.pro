"""
Consultation workflow routes.

Consultations are stored as MedicalRecord rows so clinical notes remain in the
shared patient record while exposing a workflow-oriented API for doctors.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List

from app.extensions import db_session, get_db
from app.models.appointment import Appointment
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.user import User
from app.schemas.consultations import (
    ConsultationResponse,
    ConsultationStart,
    ConsultationUpdate,
)
from app.services.clinical_workflow_service import ClinicalWorkflowService
from app.services.medical_record_service import MedicalRecordService
from app.services.realtime_service import publish_tenant_event
from app.utils.branch_scope import belongs_to_branch, user_branch_id
from app.utils.dependencies import role_required
from app.utils.pagination import apply_pagination
from app.utils.validators import Validators

router = APIRouter(prefix="/consultations", tags=["consultations"])


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


def _apply_branch_patient_scope(query, current_user: User):
    branch_id = None if current_user.role == "ADMIN" else user_branch_id(current_user)
    if not branch_id:
        return query
    return query.join(Patient, MedicalRecord.patient_id == Patient.id).filter(
        Patient.facility_slug == current_user.facility_slug,
        Patient.is_active == True,
        (Patient.branch_id == branch_id) | (Patient.department_id == branch_id),
    )


def _get_appointment(appointment_id: str | None, facility_slug: str) -> Appointment | None:
    if not appointment_id:
        return None
    appointment = db_session.query(Appointment).filter_by(
        id=appointment_id,
        facility_slug=facility_slug,
    ).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


def _consultation_status(record: MedicalRecord) -> str:
    appointment = getattr(record, "appointment", None)
    if appointment and appointment.status == "COMPLETED":
        return "completed"
    if record.diagnosis or record.treatment_plan:
        return "in_progress"
    return "started"


def _consultation_response(record: MedicalRecord) -> ConsultationResponse:
    patient = record.patient
    appointment = getattr(record, "appointment", None)
    notes = record.notes or ""
    radiology_orders = []
    if isinstance(record.lab_orders, list):
        radiology_orders = [
            order for order in record.lab_orders if isinstance(order, dict) and order.get("type") == "radiology"
        ]
    lab_orders = [
        order
        for order in (record.lab_orders or [])
        if not (isinstance(order, dict) and order.get("type") == "radiology")
    ]

    return ConsultationResponse(
        id=str(record.id),
        patient_id=str(record.patient_id),
        patient_name=patient.full_name if patient else "Unknown patient",
        appointment_id=str(record.appointment_id) if record.appointment_id else None,
        appointment_status=appointment.status if appointment else None,
        chief_complaint=record.chief_complaint,
        vital_signs=record.vital_signs or {},
        symptoms=record.symptoms or [],
        diagnosis=record.diagnosis or [],
        treatment_plan=record.treatment_plan,
        prescriptions=record.prescriptions or [],
        lab_orders=lab_orders,
        radiology_orders=radiology_orders,
        follow_up_date=record.follow_up_date.isoformat() if record.follow_up_date else None,
        notes=notes,
        created_by=str(record.created_by),
        facility_slug=record.facility_slug or "",
        status=_consultation_status(record),
        created_at=record.created_at.isoformat() if record.created_at else "",
        updated_at=record.updated_at.isoformat() if record.updated_at else None,
    )


def _publish_consultation_event(event_type: str, record: MedicalRecord, patient: Patient | None = None) -> None:
    patient = patient or record.patient
    publish_tenant_event(
        event_type=event_type,
        facility_slug=record.facility_slug or "",
        branch_id=(patient.branch_id or patient.department_id) if patient else None,
        roles=["ADMIN", "BRANCH_ADMIN", "DOCTOR", "NURSE"],
        modules=["consultations", "records"],
        resource_id=record.id,
        payload={"patient_id": record.patient_id, "appointment_id": record.appointment_id},
    )


@router.get("", response_model=List[ConsultationResponse])
async def list_consultations(
    patient_id: Optional[str] = Query(None),
    appointment_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    current_user: User = Depends(role_required("ADMIN", "BRANCH_ADMIN", "DOCTOR", "NURSE")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    query = db_session.query(MedicalRecord).filter_by(facility_slug=facility_slug)
    query = _apply_branch_patient_scope(query, current_user)
    if patient_id:
        _get_patient(patient_id, facility_slug, current_user)
        query = query.filter(MedicalRecord.patient_id == patient_id)
    if appointment_id:
        _get_appointment(appointment_id, facility_slug)
        query = query.filter(MedicalRecord.appointment_id == appointment_id)

    records = apply_pagination(query.order_by(MedicalRecord.created_at.desc()), page, per_page).all()
    return [_consultation_response(record) for record in records]


@router.post("/start", response_model=ConsultationResponse, status_code=status.HTTP_201_CREATED)
async def start_consultation(
    data: ConsultationStart,
    current_user: User = Depends(role_required("ADMIN", "BRANCH_ADMIN", "DOCTOR")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    patient = _get_patient(data.patient_id, facility_slug, current_user)
    appointment = _get_appointment(data.appointment_id, facility_slug)
    if appointment and appointment.patient_id != patient.id:
        raise HTTPException(status_code=400, detail="Appointment does not belong to patient")

    existing = None
    if appointment:
        existing = db_session.query(MedicalRecord).filter_by(
            facility_slug=facility_slug,
            appointment_id=appointment.id,
        ).first()
    if existing:
        if existing.created_by != current_user.id and current_user.role != "ADMIN":
            raise HTTPException(status_code=403, detail="Consultation belongs to another clinician")
        return _consultation_response(existing)

    record = MedicalRecordService.create_medical_record(
        {
            "patient_id": patient.id,
            "appointment_id": appointment.id if appointment else None,
            "chief_complaint": Validators.sanitize_string(data.chief_complaint or ""),
            "vital_signs": {},
            "symptoms": [],
            "diagnosis": [],
            "treatment_plan": None,
            "prescriptions": [],
            "lab_orders": [],
            "notes": "",
        },
        current_user.id,
        facility_slug,
    )

    if appointment and appointment.status in {"SCHEDULED", "CONFIRMED"}:
        appointment.status = "IN_PROGRESS"
        db_session.add(appointment)
        db_session.commit()
        db_session.refresh(record)
    _publish_consultation_event("consultation.started", record, patient)

    return _consultation_response(record)


@router.get("/{consultation_id}", response_model=ConsultationResponse)
async def get_consultation(
    consultation_id: str,
    current_user: User = Depends(role_required("ADMIN", "BRANCH_ADMIN", "DOCTOR", "NURSE")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    record = db_session.query(MedicalRecord).filter_by(
        id=consultation_id,
        facility_slug=facility_slug,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Consultation not found")
    _get_patient(str(record.patient_id), facility_slug, current_user)
    return _consultation_response(record)


@router.put("/{consultation_id}", response_model=ConsultationResponse)
async def update_consultation(
    consultation_id: str,
    data: ConsultationUpdate,
    current_user: User = Depends(role_required("ADMIN", "BRANCH_ADMIN", "DOCTOR", "NURSE")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    record = db_session.query(MedicalRecord).filter_by(
        id=consultation_id,
        facility_slug=facility_slug,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Consultation not found")
    _get_patient(str(record.patient_id), facility_slug, current_user)

    payload = data.model_dump(exclude_unset=True)
    if "chief_complaint" in payload and payload["chief_complaint"] is not None:
        payload["chief_complaint"] = Validators.sanitize_string(payload["chief_complaint"])
    if "treatment_plan" in payload and payload["treatment_plan"] is not None:
        payload["treatment_plan"] = Validators.sanitize_string(payload["treatment_plan"])
    if "notes" in payload and payload["notes"] is not None:
        payload["notes"] = Validators.sanitize_string(payload["notes"])

    provided_lab_orders = payload.pop("lab_orders", None)
    radiology_orders = payload.pop("radiology_orders", None)
    if provided_lab_orders is not None or radiology_orders is not None:
        base_lab_orders = (
            list(provided_lab_orders or [])
            if provided_lab_orders is not None
            else [
                order
                for order in (record.lab_orders or [])
                if not (isinstance(order, dict) and order.get("type") == "radiology")
            ]
        )
        payload["lab_orders"] = base_lab_orders + [
            {**order, "type": "radiology"} for order in (radiology_orders or [])
        ]

    should_sync_orders = any(
        key in data.model_fields_set
        for key in {"lab_orders", "radiology_orders", "prescriptions"}
    )
    updated = MedicalRecordService.update_medical_record(record, payload)
    if should_sync_orders:
        ClinicalWorkflowService.sync_consultation_orders(updated, current_user)
        db_session.commit()
        db_session.refresh(updated)
    patient = _get_patient(str(updated.patient_id), facility_slug, current_user)
    _publish_consultation_event("consultation.updated", updated, patient)
    return _consultation_response(updated)


@router.post("/{consultation_id}/complete", response_model=ConsultationResponse)
async def complete_consultation(
    consultation_id: str,
    current_user: User = Depends(role_required("ADMIN", "BRANCH_ADMIN", "DOCTOR")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    record = db_session.query(MedicalRecord).filter_by(
        id=consultation_id,
        facility_slug=facility_slug,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Consultation not found")
    _get_patient(str(record.patient_id), facility_slug, current_user)

    if not record.diagnosis and not record.treatment_plan:
        raise HTTPException(status_code=400, detail="Diagnosis or treatment plan is required before completion")

    appointment = _get_appointment(record.appointment_id, facility_slug)
    if appointment:
        appointment.status = "COMPLETED"
        db_session.add(appointment)
        db_session.commit()
        db_session.refresh(record)
    patient = _get_patient(str(record.patient_id), facility_slug, current_user)
    _publish_consultation_event("consultation.completed", record, patient)

    return _consultation_response(record)
