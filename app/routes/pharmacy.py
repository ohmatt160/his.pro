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
from app.services.pharmacy_service import PharmacyService
from app.utils.dependencies import get_current_user, role_required
from app.models.user import User
from app.models.patient import Patient
from app.models.facility import Facility

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pharmacy", tags=["pharmacy"])


class MedicationCreate(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50)
    generic_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None)
    category: Optional[str] = Field(None, max_length=50)
    unit: Optional[str] = Field(None, max_length=20)
    strength: Optional[str] = Field(None, max_length=50)
    price: Optional[float] = Field(None, ge=0)
    reorder_level: Optional[int] = Field(None, ge=0)


class MedicationResponse(BaseModel):
    id: str
    name: str
    code: str
    generic_name: Optional[str]
    description: Optional[str]
    category: Optional[str]
    unit: Optional[str]
    strength: Optional[str]
    price: Optional[float]
    reorder_level: Optional[int]
    is_active: bool
    facility_slug: Optional[str]
    created_at: str
    updated_at: Optional[str]


class InventoryCreate(BaseModel):
    quantity: int = Field(..., ge=0)
    expiry_date: Optional[str] = Field(None)
    batch_number: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=100)


class InventoryResponse(BaseModel):
    id: str
    medication_id: str
    quantity: int
    expiry_date: Optional[str]
    batch_number: Optional[str]
    location: Optional[str]
    last_updated: str


class PrescriptionItemCreate(BaseModel):
    medication_id: str = Field(...)
    quantity: int = Field(..., gt=0)
    dosage: Optional[str] = Field(None)
    instructions: Optional[str] = Field(None)


class PrescriptionCreate(BaseModel):
    patient_id: str = Field(...)
    items: List[PrescriptionItemCreate] = Field(..., min_items=1)
    notes: Optional[str] = Field(None)


class PrescriptionResponse(BaseModel):
    id: str
    patient_id: str
    prescribed_by: str
    status: str
    notes: Optional[str]
    filled_by: Optional[str]
    filled_at: Optional[str]
    facility_slug: Optional[str]
    created_at: str
    updated_at: Optional[str]


class MessageResponse(BaseModel):
    message: str


# ==================== Medications ====================

@router.get("/medications", response_model=List[MedicationResponse])
async def get_medications(
    active_only: bool = Query(True),
    current_user: User = Depends(role_required('ADMIN', 'PHARMACIST', 'DOCTOR')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    medications = PharmacyService.get_all_medications(facility_slug=facility_slug, active_only=active_only)

    return [
        MedicationResponse(
            id=str(m.id),
            name=m.name,
            code=m.code,
            generic_name=m.generic_name,
            description=m.description,
            category=m.category,
            unit=m.unit,
            strength=m.strength,
            price=m.price,
            reorder_level=m.reorder_level,
            is_active=m.is_active,
            facility_slug=m.facility_slug,
            created_at=m.created_at.isoformat() if m.created_at else "",
            updated_at=m.updated_at.isoformat() if m.updated_at else None
        ) for m in medications
    ]


@router.post("/medications", response_model=MedicationResponse, status_code=status.HTTP_201_CREATED)
async def create_medication(
    data: MedicationCreate,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    payload = data.dict()
    payload['facility_slug'] = facility_slug

    medication, error = PharmacyService.create_medication(payload)
    if error:
        raise HTTPException(status_code=400, detail=error)

    return MedicationResponse(
        id=str(medication.id),
        name=medication.name,
        code=medication.code,
        generic_name=medication.generic_name,
        description=medication.description,
        category=medication.category,
        unit=medication.unit,
        strength=medication.strength,
        price=medication.price,
        reorder_level=medication.reorder_level,
        is_active=medication.is_active,
        facility_slug=medication.facility_slug,
        created_at=medication.created_at.isoformat() if medication.created_at else "",
        updated_at=medication.updated_at.isoformat() if medication.updated_at else None
    )


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

    return MedicationResponse(
        id=str(medication.id),
        name=medication.name,
        code=medication.code,
        generic_name=medication.generic_name,
        description=medication.description,
        category=medication.category,
        unit=medication.unit,
        strength=medication.strength,
        price=medication.price,
        reorder_level=medication.reorder_level,
        is_active=medication.is_active,
        facility_slug=medication.facility_slug,
        created_at=medication.created_at.isoformat() if medication.created_at else "",
        updated_at=medication.updated_at.isoformat() if medication.updated_at else None
    )


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

    updated_medication = PharmacyService.update_medication(medication, data.dict(exclude_unset=True))

    return MedicationResponse(
        id=str(updated_medication.id),
        name=updated_medication.name,
        code=updated_medication.code,
        generic_name=updated_medication.generic_name,
        description=updated_medication.description,
        category=updated_medication.category,
        unit=updated_medication.unit,
        strength=updated_medication.strength,
        price=updated_medication.price,
        reorder_level=updated_medication.reorder_level,
        is_active=updated_medication.is_active,
        facility_slug=updated_medication.facility_slug,
        created_at=updated_medication.created_at.isoformat() if updated_medication.created_at else "",
        updated_at=updated_medication.updated_at.isoformat() if updated_medication.updated_at else None
    )


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

    return InventoryResponse(
        id=str(inventory.id),
        medication_id=str(inventory.medication_id),
        quantity=inventory.quantity,
        expiry_date=inventory.expiry_date.isoformat() if inventory.expiry_date else None,
        batch_number=inventory.batch_number,
        location=inventory.location,
        last_updated=inventory.last_updated.isoformat() if inventory.last_updated else ""
    )


@router.post("/inventory/{medication_id}", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
async def add_inventory(
    medication_id: str,
    data: InventoryCreate,
    current_user: User = Depends(role_required('ADMIN', 'PHARMACIST')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    inventory, error = PharmacyService.add_inventory(medication_id, facility_slug, data.dict())
    if error:
        raise HTTPException(status_code=400, detail=error)

    return InventoryResponse(
        id=str(inventory.id),
        medication_id=str(inventory.medication_id),
        quantity=inventory.quantity,
        expiry_date=inventory.expiry_date.isoformat() if inventory.expiry_date else None,
        batch_number=inventory.batch_number,
        location=inventory.location,
        last_updated=inventory.last_updated.isoformat() if inventory.last_updated else ""
    )


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

    return [
        PrescriptionResponse(
            id=str(p.id),
            patient_id=str(p.patient_id),
            prescribed_by=str(p.prescribed_by),
            status=p.status,
            notes=p.notes,
            filled_by=str(p.filled_by) if p.filled_by else None,
            filled_at=p.filled_at.isoformat() if p.filled_at else None,
            facility_slug=p.facility_slug,
            created_at=p.created_at.isoformat() if p.created_at else "",
            updated_at=p.updated_at.isoformat() if p.updated_at else None
        ) for p in prescriptions
    ]


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

    payload = data.dict()
    payload['facility_slug'] = facility_slug

    prescription = PharmacyService.create_prescription(payload, current_user.id)

    return PrescriptionResponse(
        id=str(prescription.id),
        patient_id=str(prescription.patient_id),
        prescribed_by=str(prescription.prescribed_by),
        status=prescription.status,
        notes=prescription.notes,
        filled_by=str(prescription.filled_by) if prescription.filled_by else None,
        filled_at=prescription.filled_at.isoformat() if prescription.filled_at else None,
        facility_slug=prescription.facility_slug,
        created_at=prescription.created_at.isoformat() if prescription.created_at else "",
        updated_at=prescription.updated_at.isoformat() if prescription.updated_at else None
    )


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

    return PrescriptionResponse(
        id=str(prescription.id),
        patient_id=str(prescription.patient_id),
        prescribed_by=str(prescription.prescribed_by),
        status=prescription.status,
        notes=prescription.notes,
        filled_by=str(prescription.filled_by) if prescription.filled_by else None,
        filled_at=prescription.filled_at.isoformat() if prescription.filled_at else None,
        facility_slug=prescription.facility_slug,
        created_at=prescription.created_at.isoformat() if prescription.created_at else "",
        updated_at=prescription.updated_at.isoformat() if prescription.updated_at else None
    )


@router.post("/prescriptions/{prescription_id}/dispense", response_model=PrescriptionResponse)
async def dispense_prescription(
    prescription_id: str,
    current_user: User = Depends(role_required('ADMIN', 'PHARMACIST')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    prescription, error = PharmacyService.dispense_prescription(prescription_id, current_user.id)

    if error:
        raise HTTPException(status_code=400, detail=error)

    if not prescription or prescription.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Prescription not found")

    return PrescriptionResponse(
        id=str(prescription.id),
        patient_id=str(prescription.patient_id),
        prescribed_by=str(prescription.prescribed_by),
        status=prescription.status,
        notes=prescription.notes,
        filled_by=str(prescription.filled_by) if prescription.filled_by else None,
        filled_at=prescription.filled_at.isoformat() if prescription.filled_at else None,
        facility_slug=prescription.facility_slug,
        created_at=prescription.created_at.isoformat() if prescription.created_at else "",
        updated_at=prescription.updated_at.isoformat() if prescription.updated_at else None
    )


@router.delete("/prescriptions/{prescription_id}", response_model=MessageResponse)
async def cancel_prescription(
    prescription_id: str,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    prescription, error = PharmacyService.cancel_prescription(prescription_id)

    if error:
        raise HTTPException(status_code=400, detail=error)

    if not prescription or prescription.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Prescription not found")

    return MessageResponse(message="Prescription cancelled successfully")
