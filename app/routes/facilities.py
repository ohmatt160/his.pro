"""
Facility Routes - FastAPI Version
Converted from Flask-RESTx facility_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy import or_
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from app.extensions import get_db, db_session
from app.schemas.facilities import FacilityResponse, FacilityCreate, FacilityUpdate
from app.schemas.users import MessageResponse
from app.utils.dependencies import get_current_user, role_required
from app.utils.validators import Validators
from app.models.user import User
from app.models.facility import Facility

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/facilities", tags=["facilities"])


def build_facility_response(facility: Facility) -> FacilityResponse:
    return FacilityResponse(
        id=str(facility.id),
        name=facility.name,
        slug=facility.slug,
        type=facility.type,
        country=facility.country,
        address=facility.address,
        phone=facility.phone,
        email=facility.email,
        modules=facility.modules or [],
        settings=facility.settings or {},
        is_active=facility.is_active,
        created_at=facility.created_at.isoformat() if facility.created_at else "",
        updated_at=facility.updated_at.isoformat() if facility.updated_at else None
    )


def create_facility_record(data: FacilityCreate) -> Facility:
    name = Validators.sanitize_string(data.name)
    if not name:
        raise HTTPException(status_code=400, detail="Facility name is required")
    if not data.type:
        raise HTTPException(status_code=400, detail="Facility type is required")

    if data.type not in Facility.FACILITY_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid facility type. Must be one of: {', '.join(Facility.FACILITY_TYPES)}")

    slug = Validators.generate_slug(name)
    existing = db_session.query(Facility).filter_by(slug=slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="A facility with similar name already exists")

    facility = Facility(
        name=name,
        type=data.type,
        slug=slug,
        country=data.country or '',
        address=data.address or '',
        phone=data.phone or '',
        email=data.email or '',
        modules=data.modules or [],
        settings=data.settings or {}
    )
    db_session.add(facility)
    db_session.commit()
    db_session.refresh(facility)
    return facility


def attach_user_to_facility(user: User, facility: Facility) -> None:
    if user.facility_slug and user.facility_slug != facility.slug:
        raise HTTPException(
            status_code=409,
            detail="User already belongs to another facility"
        )

    if user.facility_slug != facility.slug:
        user.facility_slug = facility.slug
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)


@router.get("", response_model=List[FacilityResponse])
async def get_facilities(
    search: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Get all facilities (admin only)"""
    query = db_session.query(Facility).filter_by(is_active=True)

    if search:
        query = query.filter(Facility.name.ilike(f'%{search}%'))

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page

    return [build_facility_response(f) for f in items]


@router.post("", response_model=FacilityResponse, status_code=status.HTTP_201_CREATED)
async def create_facility(
    data: FacilityCreate,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Create a new facility (admin only)"""
    return build_facility_response(create_facility_record(data))


@router.post("/ensure", response_model=FacilityResponse)
async def ensure_facility(
    data: FacilityCreate,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Create a facility once, or return the existing facility for setup retries."""
    slug = Validators.generate_slug(Validators.sanitize_string(data.name))
    existing = db_session.query(Facility).filter_by(slug=slug, is_active=True).first()
    if existing:
        attach_user_to_facility(current_user, existing)
        return build_facility_response(existing)

    facility = create_facility_record(data)
    attach_user_to_facility(current_user, facility)
    return build_facility_response(facility)


@router.get("/{facility_id}", response_model=FacilityResponse)
async def get_facility(
    facility_id: str,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Get facility by ID or slug (admin only)"""
    facility = (
        db_session.query(Facility)
        .filter(
            Facility.is_active == True,
            or_(Facility.id == facility_id, Facility.slug == facility_id),
        )
        .first()
    )
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    return build_facility_response(facility)


@router.put("/{facility_id}", response_model=FacilityResponse)
async def update_facility(
    facility_id: str,
    data: FacilityUpdate,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Update facility (admin only)"""
    facility = db_session.query(Facility).filter_by(id=facility_id, is_active=True).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    if data.name is not None:
        facility.name = Validators.sanitize_string(data.name)
    if data.type is not None:
        if data.type not in Facility.FACILITY_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid facility type. Must be one of: {', '.join(Facility.FACILITY_TYPES)}")
        facility.type = data.type
    if data.country is not None:
        facility.country = Validators.sanitize_string(data.country)
    if data.address is not None:
        facility.address = Validators.sanitize_string(data.address)
    if data.phone is not None:
        facility.phone = Validators.sanitize_string(data.phone)
    if data.email is not None:
        facility.email = Validators.sanitize_string(data.email)
    if data.settings is not None:
        facility.settings = data.settings

    facility.save()
    db_session.commit()

    return build_facility_response(facility)


@router.delete("/{facility_id}", response_model=MessageResponse)
async def deactivate_facility(
    facility_id: str,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Deactivate facility (soft delete)"""
    facility = db_session.query(Facility).filter_by(id=facility_id, is_active=True).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    # Check if facility has active users
    active_users = [u for u in facility.users if u.is_active]
    if active_users:
        raise HTTPException(status_code=400, detail="Cannot deactivate facility with active users")

    facility.is_active = False
    facility.save()
    db_session.commit()

    return MessageResponse(message="Facility deactivated successfully")


@router.put("/{facility_id}/modules", response_model=FacilityResponse)
async def update_facility_modules(
    facility_id: str,
    modules: List[str] = Body(...),
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Update enabled modules for a facility"""
    facility = db_session.query(Facility).filter_by(id=facility_id, is_active=True).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    # Validate modules
    valid_modules = Facility.AVAILABLE_MODULES if hasattr(Facility, 'AVAILABLE_MODULES') else []
    for module in modules:
        if module not in valid_modules:
            raise HTTPException(status_code=400, detail=f"Invalid module: {module}")

    facility.modules = modules
    facility.save()
    db_session.commit()

    return build_facility_response(facility)
