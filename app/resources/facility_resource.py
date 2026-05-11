"""
Facility Routes - FastAPI Version
Converted from Flask-RESTx facility_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging

from app.extensions import get_db, db_session
from app.utils.dependencies import get_current_user, role_required, optional_user
from app.utils.validators import Validators
from app.utils.rate_limiter import rate_limit_by_ip, AUTH_RATE_LIMIT
from app.models.user import User
from app.models.facility import Facility

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/facilities", tags=["facilities"])


# Pydantic Models
class FacilityCreate(BaseModel):
    name: str = Field(..., min_length=1)
    type: str = Field(..., description="Facility type")
    country: Optional[str] = Field("")
    address: Optional[str] = Field("")
    phone: Optional[str] = Field("")
    email: Optional[str] = Field("")
    modules: Optional[List[str]] = Field([])
    settings: Optional[Dict[str, Any]] = Field({})


class FacilityUpdate(BaseModel):
    name: Optional[str] = Field(None)
    type: Optional[str] = Field(None)
    country: Optional[str] = Field(None)
    address: Optional[str] = Field(None)
    phone: Optional[str] = Field(None)
    email: Optional[str] = Field(None)
    settings: Optional[Dict[str, Any]] = Field(None)


class FacilityModulesUpdate(BaseModel):
    modules: List[str] = Field(..., min_length=1)


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
    settings: Dict[str, Any]
    is_active: bool
    created_at: str
    updated_at: Optional[str]


class FacilityListResponse(BaseModel):
    facilities: List[FacilityResponse]
    total: int
    page: int
    per_page: int
    pages: int


class MessageResponse(BaseModel):
    message: str


@router.get("", response_model=FacilityListResponse)
async def list_facilities(
        request: Request,
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
        search: Optional[str] = Query(None),
        db: Session = Depends(get_db)
):
    """Get paginated list of facilities - public endpoint"""
    query = db_session.query(Facility).filter_by(is_active=True)

    if search:
        query = query.filter(Facility.name.ilike(f'%{search}%'))

    total = query.count()
    facilities = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page

    return FacilityListResponse(
        facilities=[f.to_dict() for f in facilities],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.post("", response_model=FacilityResponse, status_code=status.HTTP_201_CREATED)
async def create_facility(
        data: FacilityCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    """Create a new facility - public endpoint for initial setup"""
    # Validate facility type
    if data.type not in Facility.FACILITY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid facility type. Must be one of: {', '.join(Facility.FACILITY_TYPES)}"
        )

    # Check for duplicate slug
    slug = Validators.generate_slug(data.name)
    existing = db_session.query(Facility).filter_by(slug=slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="A facility with similar name already exists")

    # Create facility
    facility = Facility(
        name=Validators.sanitize_string(data.name),
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

    return facility.to_dict()


@router.get("/{slug}", response_model=FacilityResponse)
async def get_facility(
        slug: str,
        db: Session = Depends(get_db)
):
    """Get facility by slug - public endpoint"""
    facility = db_session.query(Facility).filter_by(slug=slug, is_active=True).first()

    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    return facility.to_dict()


@router.put("/{slug}", response_model=FacilityResponse)
async def update_facility(
        slug: str,
        data: FacilityUpdate,
        current_user: User = Depends(role_required('ADMIN')),
        db: Session = Depends(get_db)
):
    """Update facility"""
    facility = db_session.query(Facility).filter_by(slug=slug, is_active=True).first()

    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    # Update fields
    if data.name is not None and data.name:
        facility.name = Validators.sanitize_string(data.name)
    if data.type is not None:
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

    db_session.commit()
    db_session.refresh(facility)

    return facility.to_dict()


@router.delete("/{slug}", response_model=MessageResponse)
async def deactivate_facility(
        slug: str,
        current_user: User = Depends(role_required('ADMIN')),
        db: Session = Depends(get_db)
):
    """Deactivate facility (soft delete)"""
    facility = db_session.query(Facility).filter_by(slug=slug, is_active=True).first()

    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    # Check if facility has active users
    active_users = [u for u in facility.users if u.is_active]
    if active_users:
        raise HTTPException(status_code=400, detail="Cannot deactivate facility with active users")

    facility.is_active = False
    db_session.commit()

    return MessageResponse(message="Facility deactivated successfully")


@router.put("/{slug}/modules", response_model=FacilityResponse)
async def update_facility_modules(
        slug: str,
        data: FacilityModulesUpdate,
        current_user: User = Depends(role_required('ADMIN')),
        db: Session = Depends(get_db)
):
    """Update enabled modules for a facility"""
    facility = db_session.query(Facility).filter_by(slug=slug, is_active=True).first()

    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    # Validate modules
    valid_modules = Facility.AVAILABLE_MODULES
    for module in data.modules:
        if module not in valid_modules:
            raise HTTPException(status_code=400, detail=f"Invalid module: {module}")

    facility.modules = data.modules
    db_session.commit()
    db_session.refresh(facility)

    return facility.to_dict()