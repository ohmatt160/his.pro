"""
Facility Routes - FastAPI Version
Converted from Flask-RESTx facility_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from app.extensions import get_db, db_session
from app.utils.dependencies import get_current_user, role_required
from app.utils.validators import Validators
from app.models.user import User
from app.models.facility import Facility

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/facilities", tags=["facilities"])


class FacilityCreate(BaseModel):
    name: str = Field(..., max_length=100)
    type: str = Field(..., max_length=50)
    country: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=120)
    modules: Optional[List[str]] = Field(default_factory=list)
    settings: Optional[dict] = Field(default_factory=dict)


class FacilityUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    type: Optional[str] = Field(None, max_length=50)
    country: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=120)
    settings: Optional[dict] = None


class FacilityResponse(BaseModel):
    id: str
    name: str
    slug: str
    type: str
    country: Optional[str]
    address: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    modules: List[str]
    settings: dict
    is_active: bool
    created_at: str
    updated_at: Optional[str]


class MessageResponse(BaseModel):
    message: str


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

    return [
        FacilityResponse(
            id=str(f.id),
            name=f.name,
            slug=f.slug,
            type=f.type,
            country=f.country,
            address=f.address,
            phone=f.phone,
            email=f.email,
            modules=f.modules or [],
            settings=f.settings or {},
            is_active=f.is_active,
            created_at=f.created_at.isoformat() if f.created_at else "",
            updated_at=f.updated_at.isoformat() if f.updated_at else None
        ) for f in items
    ]


@router.post("", response_model=FacilityResponse, status_code=status.HTTP_201_CREATED)
async def create_facility(
    data: FacilityCreate,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Create a new facility (admin only)"""
    name = Validators.sanitize_string(data.name)
    if not name:
        raise HTTPException(status_code=400, detail="Facility name is required")
    if not data.type:
        raise HTTPException(status_code=400, detail="Facility type is required")

    # Validate facility type
    if data.type not in Facility.FACILITY_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid facility type. Must be one of: {', '.join(Facility.FACILITY_TYPES)}")

    # Generate slug
    slug = Validators.generate_slug(name)

    # Check duplicate slug
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


@router.get("/{facility_id}", response_model=FacilityResponse)
async def get_facility(
    facility_id: str,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Get facility by ID (admin only)"""
    facility = db_session.query(Facility).filter_by(id=facility_id, is_active=True).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

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
