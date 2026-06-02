"""
Facility Routes - FastAPI Version
Converted from Flask-RESTx facility_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional, List
import logging
import secrets
import string

from app.extensions import get_db, db_session
from app.schemas.facilities import FacilityResponse, FacilityCreate, FacilityUpdate
from app.schemas.users import MessageResponse, FacilityStaffCreate, FacilityStaffResponse
from app.utils.dependencies import get_current_user, role_required
from app.utils.validators import Validators
from app.models.user import User
from app.models.facility import Facility
from app.services.audit_log_service import AuditLogService

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


FRONTEND_TO_BACKEND_ROLE = {
    "doctor": "DOCTOR",
    "nurse": "NURSE",
    "reception": "RECEPTIONIST",
    "pharmacist": "PHARMACIST",
    "lab": "LAB_TECH",
}

BACKEND_TO_FRONTEND_ROLE = {
    "ADMIN": "admin",
    "DOCTOR": "doctor",
    "NURSE": "nurse",
    "RECEPTIONIST": "reception",
    "PHARMACIST": "pharmacist",
    "LAB_TECH": "lab",
}

ROLE_PREFIX = {
    "ADMIN": "ADM",
    "DOCTOR": "DOC",
    "NURSE": "NUR",
    "RECEPTIONIST": "REC",
    "PHARMACIST": "PHA",
    "LAB_TECH": "LAB",
}


def require_admin_for_facility(user: User, facility_slug: str) -> None:
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only facility admins can manage staff")

    if user.facility_slug != facility_slug:
        raise HTTPException(status_code=403, detail="Cannot manage another facility")


def split_full_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split()
    first_name = parts[0] if parts else "Staff"
    last_name = " ".join(parts[1:]) if len(parts) > 1 else "Member"
    return first_name, last_name


def generate_temporary_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(char.islower() for char in password)
            and any(char.isupper() for char in password)
            and any(char.isdigit() for char in password)
        ):
            return password


def next_staff_login_id(facility_slug: str, role: str) -> str:
    prefix = ROLE_PREFIX[role]
    existing_count = (
        db_session.query(User)
        .filter(User.facility_slug == facility_slug, User.role == role)
        .count()
    )
    return f"{prefix}-{existing_count + 1:03d}"


def build_staff_response(
    user: User,
    temporary_password: str = "",
    created_by: str | None = None,
) -> FacilityStaffResponse:
    full_name = " ".join(
        part for part in [user.first_name, user.last_name] if part
    ).strip() or user.username

    return FacilityStaffResponse(
        staffRecordId=str(user.id),
        facilitySlug=user.facility_slug or "",
        fullName=full_name,
        role=BACKEND_TO_FRONTEND_ROLE.get(user.role, "reception"),
        department=user.department or "",
        email=user.email,
        phone=user.phone or "—",
        loginId=user.username,
        password=temporary_password,
        temporaryPassword=temporary_password,
        mustChangePassword=bool(user.must_change_password),
        status="active" if user.is_active else "inactive",
        createdAt=user.created_at.isoformat() if user.created_at else "",
        createdBy=created_by,
    )


def get_facility_or_404(facility_slug: str) -> Facility:
    facility = db_session.query(Facility).filter_by(slug=facility_slug, is_active=True).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    return facility


def get_current_admin_facility(current_user: User) -> Facility:
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    if not current_user.facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")
    return get_facility_or_404(current_user.facility_slug)


@router.get("", response_model=List[FacilityResponse])
async def get_facilities(
    search: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Get all facilities (admin only)"""
    facility = get_current_admin_facility(current_user)

    if search:
        if search.lower() not in facility.name.lower():
            return []

    return [build_facility_response(facility)]


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


@router.get("/{facility_slug}/staff", response_model=List[FacilityStaffResponse])
async def get_facility_staff(
    facility_slug: str,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """List active staff accounts for a facility."""
    get_facility_or_404(facility_slug)
    require_admin_for_facility(current_user, facility_slug)

    staff = (
        db_session.query(User)
        .filter(User.facility_slug == facility_slug, User.is_active == True)
        .order_by(User.created_at.asc())
        .all()
    )

    return [build_staff_response(member) for member in staff]


@router.post(
    "/{facility_slug}/staff",
    response_model=FacilityStaffResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_facility_staff(
    facility_slug: str,
    data: FacilityStaffCreate,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Create a staff user for a facility and return one-time credentials."""
    get_facility_or_404(facility_slug)
    require_admin_for_facility(current_user, facility_slug)

    frontend_role = data.role.lower()
    role = FRONTEND_TO_BACKEND_ROLE.get(frontend_role, data.role.upper())
    if role not in ROLE_PREFIX or role == "ADMIN":
        raise HTTPException(status_code=400, detail="Invalid staff role")

    full_name = Validators.sanitize_string(data.fullName)
    department = Validators.sanitize_string(data.department)
    first_name, last_name = split_full_name(full_name)
    login_id = next_staff_login_id(facility_slug, role)
    email = str(data.email).lower() if data.email else f"{login_id.lower()}@{facility_slug}.hispro.local"
    phone = Validators.sanitize_string(data.phone or "—")
    temporary_password = data.password or generate_temporary_password()
    is_valid_password, password_error = Validators.validate_password(temporary_password)
    if not is_valid_password:
        raise HTTPException(status_code=400, detail=password_error)

    if db_session.query(User).filter_by(username=login_id).first():
        raise HTTPException(status_code=409, detail="Generated login ID already exists")

    if db_session.query(User).filter_by(email=email).first():
        raise HTTPException(status_code=409, detail="Email already exists")

    user = User(
        username=login_id,
        email=email,
        role=role,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        department=department,
        facility_slug=facility_slug,
        must_change_password=True,
    )
    user.set_password(temporary_password)

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return build_staff_response(
        user,
        temporary_password=temporary_password,
        created_by=data.createdBy or current_user.username,
    )


@router.get("/{facility_slug}/staff/{login_id}", response_model=FacilityStaffResponse)
async def get_facility_staff_member(
    facility_slug: str,
    login_id: str,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Get one staff account by login ID."""
    get_facility_or_404(facility_slug)
    require_admin_for_facility(current_user, facility_slug)

    member = (
        db_session.query(User)
        .filter(
            User.facility_slug == facility_slug,
            User.username == login_id,
            User.is_active == True,
        )
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Staff member not found")

    return build_staff_response(member)


@router.get("/{facility_id}", response_model=FacilityResponse)
async def get_facility(
    facility_id: str,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Get facility by ID or slug (admin only)"""
    facility = get_current_admin_facility(current_user)
    if facility_id not in {facility.id, facility.slug}:
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
    facility = get_current_admin_facility(current_user)
    if facility_id not in {facility.id, facility.slug}:
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

    AuditLogService.log_action(
        user_id=current_user.id,
        action="UPDATE_FACILITY",
        resource_type="facility",
        resource_id=facility.id,
        facility_slug=facility.slug,
        details={"fields": sorted(data.model_dump(exclude_unset=True).keys())},
    )

    return build_facility_response(facility)


@router.delete("/{facility_id}", response_model=MessageResponse)
async def deactivate_facility(
    facility_id: str,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Deactivate facility (soft delete)"""
    facility = get_current_admin_facility(current_user)
    if facility_id not in {facility.id, facility.slug}:
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
    facility = get_current_admin_facility(current_user)
    if facility_id not in {facility.id, facility.slug}:
        raise HTTPException(status_code=404, detail="Facility not found")

    # Validate modules
    valid_modules = Facility.AVAILABLE_MODULES if hasattr(Facility, 'AVAILABLE_MODULES') else []
    for module in modules:
        if module not in valid_modules:
            raise HTTPException(status_code=400, detail=f"Invalid module: {module}")

    facility.modules = modules
    facility.save()
    db_session.commit()

    AuditLogService.log_action(
        user_id=current_user.id,
        action="UPDATE_FACILITY_MODULES",
        resource_type="facility",
        resource_id=facility.id,
        facility_slug=facility.slug,
        details={"modules": modules},
    )

    return build_facility_response(facility)
