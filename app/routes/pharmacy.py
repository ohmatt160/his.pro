"""
Pharmacy Routes - FastAPI Version
Converted from Flask-RESTx pharmacy_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from app.extensions import get_db
from app.schemas.pharmacy import (
    InventoryCreate,
    InventoryResponse,
    MedicationResponse,
    PrescriptionCreate,
    PrescriptionResponse,
    MedicationCreate,
)
from app.schemas.users import MessageResponse
from app.services.clinical_workflow_service import ClinicalWorkflowService
from app.services.order_workflow_service import OrderWorkflowService
from app.services.patient_notification_service import PatientNotificationService
from app.services.pharmacy_service import PharmacyService
from app.utils.dependencies import get_current_user, role_required
from app.models.user import User
from app.models.patient import Patient
from app.models.facility import Facility

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pharmacy", tags=["pharmacy"])


def _medication_response(medication) -> MedicationResponse:
    return MedicationResponse(
        id=str(medication.id),
        name=medication.name,
        code=medication.code,
        generic_name=medication.generic_name,
        description=medication.description,
        category=medication.category,
        unit=medication.unit,
        strength=medication.strength,
        price=float(medication.price) if medication.price is not None else None,
        reorder_level=medication.reorder_level,
        is_active=medication.is_active,
        facility_slug=medication.facility_slug,
        created_at=medication.created_at.isoformat() if medication.created_at else "",
        updated_at=medication.updated_at.isoformat() if medication.updated_at else None
    )


def _inventory_response(inventory) -> InventoryResponse:
    return InventoryResponse(
        id=str(inventory.id),
        medication_id=str(inventory.medication_id),
        quantity=inventory.quantity,
        expiry_date=inventory.expiry_date.isoformat() if inventory.expiry_date else None,
        batch_number=inventory.batch_number,
        location=inventory.location,
        last_updated=inventory.updated_at.isoformat() if inventory.updated_at else ""
    )


def _prescription_response(prescription) -> PrescriptionResponse:
    return PrescriptionResponse(
        id=str(prescription.id),
        patient_id=str(prescription.patient_id),
        prescribed_by=str(prescription.prescribed_by),
        status=prescription.status,
        notes=prescription.notes,
        filled_by=str(prescription.dispensed_by) if prescription.dispensed_by else None,
        filled_at=prescription.dispensed_date.isoformat() if prescription.dispensed_date else None,
        facility_slug=prescription.facility_slug,
        created_at=prescription.created_at.isoformat() if prescription.created_at else "",
        updated_at=prescription.updated_at.isoformat() if prescription.updated_at else None
    )


# ==================== Medications ====================



@router.get("/medications", response_model=List[MedicationResponse])
async def get_medications(
    active_only: bool = Query(True),
    current_user: User = Depends(role_required('ADMIN', 'PHARMACIST', 'DOCTOR')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    medications = PharmacyService.get_all_medications(facility_slug=facility_slug, active_only=active_only)

    return [_medication_response(m) for m in medications]



@router.post("/medications", response_model=MedicationResponse, status_code=status.HTTP_201_CREATED)
async def create_medication(
    data: MedicationCreate,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    payload = data.model_dump()
    payload['facility_slug'] = facility_slug

    medication, error = PharmacyService.create_medication(payload)
    if error:
        raise HTTPException(status_code=400, detail=error)

    return _medication_response(medication)


@router.get("/medications/{medication_id}", response_model=MedicationResponse)
async def get_medication(
    medication_id: str,
    current_user: User = Depends(role_required('ADMIN', 'PHARMACIST', 'DOCTOR')),
    db: Session = Depends(get_db)
):
    medication = PharmacyService.get_medication_by_id(medication_id)
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")

    if medication.facility_slug != current_user.facility_slug:
        raise HTTPException(status_code=404, detail="Medication not found")

    return _medication_response(medication)


@router.put("/medications/{medication_id}", response_model=MedicationResponse)
async def update_medication(
    medication_id: str,
    data: MedicationCreate,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    medication = PharmacyService.get_medication_by_id(medication_id)
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")

    if medication.facility_slug != current_user.facility_slug:
        raise HTTPException(status_code=404, detail="Medication not found")

    updated_medication = PharmacyService.update_medication(medication, data.model_dump(exclude_unset=True))

    return _medication_response(updated_medication)


# ==================== Inventory ====================

@router.get("/inventory/{medication_id}", response_model=InventoryResponse)
async def get_inventory(
    medication_id: str,
    current_user: User = Depends(role_required('ADMIN', 'PHARMACIST')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    inventory = PharmacyService.get_inventory(medication_id, facility_slug)

    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")

    return _inventory_response(inventory)


@router.post("/inventory/{medication_id}", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
async def add_inventory(
    medication_id: str,
    data: InventoryCreate,
    current_user: User = Depends(role_required('ADMIN', 'PHARMACIST')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    inventory, error = PharmacyService.add_inventory(medication_id, facility_slug, data.model_dump())
    if error:
        raise HTTPException(status_code=400, detail=error)

    return _inventory_response(inventory)


# ==================== Prescriptions ====================

@router.get("/prescriptions", response_model=List[PrescriptionResponse])
async def get_prescriptions(
    patient_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'PHARMACIST')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    if patient_id:
        patient = db.query(Patient).filter_by(id=patient_id, facility_slug=facility_slug).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        prescriptions = PharmacyService.get_prescriptions_by_patient(patient_id, facility_slug)
    elif status == 'PENDING':
        prescriptions = PharmacyService.get_pending_prescriptions(facility_slug)
    else:
        from app.models.pharmacy import Prescription
        prescriptions = db.query(Prescription).filter_by(facility_slug=facility_slug).order_by(Prescription.created_at.desc()).all()

    return [_prescription_response(p) for p in prescriptions]



@router.post("/prescriptions", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_prescription(
    data: PrescriptionCreate,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    # Verify patient belongs to facility
    patient = db.query(Patient).filter_by(id=data.patient_id, facility_slug=facility_slug).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    for item in data.items:
        medication = PharmacyService.get_medication_by_id(item.medication_id)
        if not medication or medication.facility_slug != facility_slug:
            raise HTTPException(status_code=404, detail="Medication not found")

    payload = data.model_dump()
    payload['facility_slug'] = facility_slug

    prescription = PharmacyService.create_prescription(payload, current_user.id)
    OrderWorkflowService.record(
        facility_slug=facility_slug,
        patient_id=prescription.patient_id,
        order_type="prescription",
        order_id=prescription.id,
        event_type="consultation_order_created",
        status=prescription.status,
        title="Prescription created",
        message="Prescription created for pharmacy dispensing.",
        actor_id=current_user.id,
        target_role="PHARMACIST",
        metadata={"items": len(data.items)},
    )

    return _prescription_response(prescription)


@router.get("/prescriptions/{prescription_id}", response_model=PrescriptionResponse)
async def get_prescription(
    prescription_id: str,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'PHARMACIST')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    prescription = PharmacyService.get_prescription_by_id(prescription_id)

    if not prescription or prescription.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Prescription not found")

    return _prescription_response(prescription)


@router.post("/prescriptions/{prescription_id}/dispense", response_model=PrescriptionResponse)
async def dispense_prescription(
    prescription_id: str,
    current_user: User = Depends(role_required('ADMIN', 'PHARMACIST')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    prescription, error = PharmacyService.dispense_prescription(
        prescription_id,
        current_user.id,
        facility_slug=facility_slug,
    )

    if error:
        raise HTTPException(status_code=400, detail=error)

    OrderWorkflowService.record(
        facility_slug=facility_slug,
        patient_id=prescription.patient_id,
        order_type="prescription",
        order_id=prescription.id,
        event_type="prescription_dispensed",
        status=prescription.status,
        title="Prescription dispensed",
        message="Prescription has been dispensed by pharmacy.",
        actor_id=current_user.id,
        target_role="DOCTOR",
        metadata={"dispensed_by": prescription.dispensed_by},
    )
    patient = db.query(Patient).filter_by(id=prescription.patient_id, facility_slug=facility_slug).first()
    if patient:
        PatientNotificationService.create(
            facility_slug=facility_slug,
            patient=patient,
            notification_type="prescription_dispensed",
            title="Prescription dispensed",
            message="Your prescription has been dispensed and is ready for pickup or collection confirmation.",
            source_type="prescription",
            source_id=prescription.id,
            metadata={"dispensed_by": prescription.dispensed_by},
        )
    ClinicalWorkflowService.notify_user(
        prescription.prescribed_by,
        facility_slug,
        "info",
        "Prescription dispensed",
        f"Prescription {prescription.id} has been dispensed.",
    )
    OrderWorkflowService.record(
        facility_slug=facility_slug,
        patient_id=prescription.patient_id,
        order_type="prescription",
        order_id=prescription.id,
        event_type="doctor_notified",
        status="NOTIFIED",
        title="Doctor notified",
        message="Prescribing clinician was notified that the prescription was dispensed.",
        actor_id=current_user.id,
        target_role="DOCTOR",
        metadata={"prescribed_by": prescription.prescribed_by},
    )

    return _prescription_response(prescription)


@router.delete("/prescriptions/{prescription_id}", response_model=MessageResponse)
async def cancel_prescription(
    prescription_id: str,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    prescription, error = PharmacyService.cancel_prescription(
        prescription_id,
        facility_slug=facility_slug,
    )

    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")

    if error:
        raise HTTPException(status_code=400, detail=error)

    return MessageResponse(message="Prescription cancelled successfully")
