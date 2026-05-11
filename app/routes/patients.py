"""
Patients Routes - FastAPI Version
Converted from Flask-RESTx patient_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from app.extensions import get_db
from app.services.patient_service import PatientService
from app.utils.validators import Validators
from app.utils.dependencies import get_current_user, role_required
from app.models.user import User
from app.models.facility import Facility

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/patients", tags=["patients"])


# Pydantic models
class PatientCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: str = Field(...)  # ISO date string
    gender: Optional[str] = Field(None, pattern="^(MALE|FEMALE|OTHER)$")
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=120)
    address: Optional[str] = Field(None)
    blood_type: Optional[str] = Field(None, pattern="^(A\\+|A-|B\\+|B-|O\\+|O-|AB\\+|AB-)$")
    medical_history: Optional[dict] = Field(default_factory=dict)
    emergency_contact_name: Optional[str] = Field(None, max_length=100)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)


class PatientUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    date_of_birth: Optional[str] = Field(None)
    gender: Optional[str] = Field(None, pattern="^(MALE|FEMALE|OTHER)$")
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=120)
    address: Optional[str] = Field(None)
    blood_type: Optional[str] = Field(None, pattern="^(A\\+|A-|B\\+|B-|O\\+|O-|AB\\+|AB-)$")
    medical_history: Optional[dict] = None
    emergency_contact_name: Optional[str] = Field(None, max_length=100)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)


class PatientResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    date_of_birth: str
    gender: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    address: Optional[str]
    blood_type: Optional[str]
    medical_history: Optional[dict]
    emergency_contact_name: Optional[str]
    emergency_contact_phone: Optional[str]
    created_by: str
    facility_slug: Optional[str]
    is_active: bool
    created_at: str
    updated_at: Optional[str]
    full_name: Optional[str]


class PatientListResponse(BaseModel):
    patients: List[PatientResponse]
    total: int
    page: int
    per_page: int
    pages: int


class MessageResponse(BaseModel):
    message: str


@router.get("", response_model=PatientListResponse)
async def get_patients(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=100),
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of patients
    """
    try:
        # Get current user's facility for filtering (multi-tenant)
        facility_slug = current_user.facility_slug if current_user else None

        # Verify facility exists and is active
        if facility_slug:
            facility = db.query(Facility).filter_by(slug=facility_slug, is_active=True).first()
            if not facility:
                raise HTTPException(status_code=403, detail="Your facility is inactive or not found")

        result = PatientService.get_all_patients(
            facility_slug=facility_slug,
            page=page,
            per_page=per_page,
            search=search
        )

        # Serialize patients
        patients_list = []
        for patient in result['items']:
            patients_list.append(PatientResponse(
                id=str(patient.id),
                first_name=patient.first_name,
                last_name=patient.last_name,
                date_of_birth=patient.date_of_birth.isoformat() if patient.date_of_birth else "",
                gender=patient.gender,
                phone=patient.phone,
                email=patient.email,
                address=patient.address,
                blood_type=patient.blood_type,
                medical_history=patient.medical_history,
                emergency_contact_name=patient.emergency_contact_name,
                emergency_contact_phone=patient.emergency_contact_phone,
                created_by=str(patient.created_by),
                facility_slug=patient.facility_slug,
                is_active=patient.is_active,
                created_at=patient.created_at.isoformat() if patient.created_at else "",
                updated_at=patient.updated_at.isoformat() if patient.updated_at else None,
                full_name=patient.full_name
            ))

        return PatientListResponse(
            patients=patients_list,
            total=result['total'],
            page=result['page'],
            per_page=result['per_page'],
            pages=result['pages']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Patients] Exception in get_patients: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve patients: {str(e)}")


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient_data: PatientCreate,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    """
    Create a new patient
    """
    try:
        # Sanitize string fields
        data = patient_data.dict()
        if 'first_name' in data:
            data['first_name'] = Validators.sanitize_string(data['first_name'])
        if 'last_name' in data:
            data['last_name'] = Validators.sanitize_string(data['last_name'])
        if data.get('phone'):
            data['phone'] = Validators.sanitize_string(data['phone'])
        if data.get('email'):
            data['email'] = Validators.sanitize_string(data['email'])
        if data.get('address'):
            data['address'] = Validators.sanitize_string(data['address'])
        if data.get('emergency_contact_name'):
            data['emergency_contact_name'] = Validators.sanitize_string(data['emergency_contact_name'])
        if data.get('emergency_contact_phone'):
            data['emergency_contact_phone'] = Validators.sanitize_string(data['emergency_contact_phone'])

        logger.info(f"[Patient] Creating patient with data: {data}")

        # Create patient
        patient = PatientService.create_patient(
            data=data,
            user_id=current_user.id,
            facility_slug=current_user.facility_slug
        )

        logger.info(f"[Patient] Patient created successfully: {patient.id}")

        # Return patient data
        return PatientResponse(
            id=str(patient.id),
            first_name=patient.first_name,
            last_name=patient.last_name,
            date_of_birth=patient.date_of_birth.isoformat() if patient.date_of_birth else "",
            gender=patient.gender,
            phone=patient.phone,
            email=patient.email,
            address=patient.address,
            blood_type=patient.blood_type,
            medical_history=patient.medical_history,
            emergency_contact_name=patient.emergency_contact_name,
            emergency_contact_phone=patient.emergency_contact_phone,
            created_by=str(patient.created_by),
            facility_slug=patient.facility_slug,
            is_active=patient.is_active,
            created_at=patient.created_at.isoformat() if patient.created_at else "",
            updated_at=patient.updated_at.isoformat() if patient.updated_at else None,
            full_name=patient.full_name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Patient] Exception creating patient: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create patient: {str(e)}")


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    """
    Get patient by ID
    """
    try:
        # Get current user's facility for filtering (multi-tenant)
        facility_slug = current_user.facility_slug if current_user else None

        if not facility_slug:
            raise HTTPException(status_code=400, detail="User is not associated with a facility")

        # Filter by facility
        patient = PatientService.get_patient_by_id(patient_id, facility_slug)

        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        return PatientResponse(
            id=str(patient.id),
            first_name=patient.first_name,
            last_name=patient.last_name,
            date_of_birth=patient.date_of_birth.isoformat() if patient.date_of_birth else "",
            gender=patient.gender,
            phone=patient.phone,
            email=patient.email,
            address=patient.address,
            blood_type=patient.blood_type,
            medical_history=patient.medical_history,
            emergency_contact_name=patient.emergency_contact_name,
            emergency_contact_phone=patient.emergency_contact_phone,
            created_by=str(patient.created_by),
            facility_slug=patient.facility_slug,
            is_active=patient.is_active,
            created_at=patient.created_at.isoformat() if patient.created_at else "",
            updated_at=patient.updated_at.isoformat() if patient.updated_at else None,
            full_name=patient.full_name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Patient] Exception getting patient {patient_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve patient: {str(e)}")


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    patient_data: PatientUpdate,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR')),
    db: Session = Depends(get_db)
):
    """
    Update patient information
    """
    try:
        # Get current user's facility for filtering (multi-tenant)
        facility_slug = current_user.facility_slug if current_user else None

        if not facility_slug:
            raise HTTPException(status_code=400, detail="User is not associated with a facility")

        # Filter by facility
        patient = PatientService.get_patient_by_id(patient_id, facility_slug)

        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        # Sanitize fields
        data = patient_data.dict(exclude_unset=True)
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = Validators.sanitize_string(value)

        # Update patient
        updated_patient = PatientService.update_patient(patient, data)

        return PatientResponse(
            id=str(updated_patient.id),
            first_name=updated_patient.first_name,
            last_name=updated_patient.last_name,
            date_of_birth=updated_patient.date_of_birth.isoformat() if updated_patient.date_of_birth else "",
            gender=updated_patient.gender,
            phone=updated_patient.phone,
            email=updated_patient.email,
            address=updated_patient.address,
            blood_type=updated_patient.blood_type,
            medical_history=updated_patient.medical_history,
            emergency_contact_name=updated_patient.emergency_contact_name,
            emergency_contact_phone=updated_patient.emergency_contact_phone,
            created_by=str(updated_patient.created_by),
            facility_slug=updated_patient.facility_slug,
            is_active=updated_patient.is_active,
            created_at=updated_patient.created_at.isoformat() if updated_patient.created_at else "",
            updated_at=updated_patient.updated_at.isoformat() if updated_patient.updated_at else None,
            full_name=updated_patient.full_name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Patient] Exception updating patient {patient_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update patient: {str(e)}")


@router.delete("/{patient_id}", response_model=MessageResponse)
async def delete_patient(
    patient_id: str,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """
    Delete patient (soft delete)
    """
    try:
        # Get current user's facility for filtering (multi-tenant)
        facility_slug = current_user.facility_slug if current_user else None

        if not facility_slug:
            raise HTTPException(status_code=400, detail="User is not associated with a facility")

        # Filter by facility
        patient = PatientService.get_patient_by_id(patient_id, facility_slug)

        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        PatientService.delete_patient(patient)

        return MessageResponse(message="Patient deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Patient] Exception deleting patient {patient_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete patient: {str(e)}")
