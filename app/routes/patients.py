"""
Patients Routes - FastAPI Version
Converted from Flask-RESTx patient_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from app.extensions import get_db
from app.schemas.patients import (
    PatientListResponse,
    PatientResponse,
    PatientCreate,
    PatientOptionResponse,
    PatientTimelineResponse,
    PatientUpdate,
)
from app.schemas.users import MessageResponse
from app.services.patient_service import PatientService
from app.services.patient_timeline_service import PatientTimelineService
from app.utils.validators import Validators
from app.utils.dependencies import get_current_user, role_required
from app.utils.branch_scope import user_branch_id
from app.models.user import User
from app.models.facility import Facility

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/patients", tags=["patients"])


def _load_patient_page(**kwargs):
    return PatientService.get_all_patients(**kwargs)


def build_patient_response(patient) -> PatientResponse:
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
        full_name=patient.full_name,
        department_id=patient.department_id,
        branch_id=patient.branch_id or patient.department_id,
    )


@router.get("/options", response_model=list[PatientOptionResponse])
async def get_patient_options(
    search: Optional[str] = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    department_id: Optional[str] = Query(None, max_length=36),
    branch_id: Optional[str] = Query(None, max_length=36),
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')),
):
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")
    rows = PatientService.get_patient_options(
        facility_slug=facility_slug,
        current_user=current_user,
        search=search,
        limit=limit,
        department_id=department_id,
        branch_id=branch_id,
    )
    return [
        PatientOptionResponse(
            id=str(row.id),
            first_name=row.first_name,
            last_name=row.last_name,
            full_name=f"{row.first_name} {row.last_name}".strip(),
            phone=row.phone,
        )
        for row in rows
    ]


@router.get("", response_model=PatientListResponse)
async def get_patients(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=100),
    department_id: Optional[str] = Query(None, max_length=36),
    branch_id: Optional[str] = Query(None, max_length=36),
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')),
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

        result = _load_patient_page(
            facility_slug=facility_slug,
            page=page,
            per_page=per_page,
            search=search,
            current_user=current_user,
            department_id=department_id,
            branch_id=branch_id,
        )

        # Serialize patients
        patients_list = []
        for patient in result['items']:
            patients_list.append(build_patient_response(patient))

        return PatientListResponse(
            patients=patients_list,
            total=result['total'],
            page=result['page'],
            per_page=result['per_page'],
            pages=result['pages']
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("[Patients] Failed to retrieve patients")
        raise HTTPException(status_code=500, detail="Patients could not be loaded")


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient_data: PatientCreate,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    """
    Create a new patient
    """
    try:
        # Sanitize string fields
        data = patient_data.model_dump()
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
        current_branch_id = user_branch_id(current_user)
        if current_user.branch_id:
            data['branch_id'] = current_user.branch_id
        elif current_branch_id:
            data['branch_id'] = current_branch_id
            data['department_id'] = current_branch_id

        logger.info(f"[Patient] Creating patient with data: {data}")

        # Create patient
        patient = PatientService.create_patient(
            data=data,
            user_id=current_user.id,
            facility_slug=current_user.facility_slug
        )

        logger.info(f"[Patient] Patient created successfully: {patient.id}")

        # Return patient data
        return build_patient_response(patient)

    except HTTPException:
        raise
    except Exception:
        logger.exception("[Patient] Failed to create patient")
        raise HTTPException(status_code=500, detail="Patient could not be created")


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')),
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

        if not PatientService.user_can_access_patient(patient_id, facility_slug, current_user):
            raise HTTPException(status_code=403, detail="You are not authorized to access this patient")

        return build_patient_response(patient)

    except HTTPException:
        raise
    except Exception:
        logger.exception("[Patient] Failed to retrieve patient %s", patient_id)
        raise HTTPException(status_code=500, detail="Patient could not be loaded")


@router.get("/{patient_id}/timeline", response_model=PatientTimelineResponse)
async def get_patient_timeline(
    patient_id: str,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    try:
        facility_slug = current_user.facility_slug if current_user else None

        if not facility_slug:
            raise HTTPException(status_code=400, detail="User is not associated with a facility")

        patient = PatientService.get_patient_by_id(patient_id, facility_slug)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        if not PatientService.user_can_access_patient(patient_id, facility_slug, current_user):
            raise HTTPException(status_code=403, detail="You are not authorized to access this patient")

        events = PatientTimelineService.build_patient_timeline(patient, facility_slug)
        return PatientTimelineResponse(
            patient=build_patient_response(patient),
            events=events,
            total=len(events),
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("[Patient] Failed to retrieve patient timeline %s", patient_id)
        raise HTTPException(status_code=500, detail="Patient timeline could not be loaded")


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    patient_data: PatientUpdate,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'RECEPTIONIST')),
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

        if not PatientService.user_can_access_patient(patient_id, facility_slug, current_user):
            raise HTTPException(status_code=403, detail="You are not authorized to access this patient")

        # Sanitize fields
        data = patient_data.model_dump(exclude_unset=True)
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = Validators.sanitize_string(value)

        # Update patient
        updated_patient = PatientService.update_patient(patient, data)

        return build_patient_response(updated_patient)

    except HTTPException:
        raise
    except Exception:
        logger.exception("[Patient] Failed to update patient %s", patient_id)
        raise HTTPException(status_code=500, detail="Patient could not be updated")


@router.delete("/{patient_id}", response_model=MessageResponse)
async def delete_patient(
    patient_id: str,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN')),
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

        if not PatientService.user_can_access_patient(patient_id, facility_slug, current_user):
            raise HTTPException(status_code=403, detail="You are not authorized to access this patient")

        PatientService.delete_patient(patient)

        return MessageResponse(message="Patient deleted successfully")

    except HTTPException:
        raise
    except Exception:
        logger.exception("[Patient] Failed to delete patient %s", patient_id)
        raise HTTPException(status_code=500, detail="Patient could not be deleted")
