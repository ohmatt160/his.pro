"""
Facility Routes - FastAPI Version
Converted from Flask-RESTx facility_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query, Body
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional, List
import logging
import secrets
import string

from app.extensions import get_db, db_session
from app.schemas.facilities import FacilityResponse, FacilityCreate, FacilityUpdate, FacilityModulesUpdate
from app.schemas.users import MessageResponse, FacilityStaffCreate, FacilityStaffUpdate, FacilityStaffResponse
from app.utils.dependencies import get_current_user, role_required
from app.utils.validators import Validators
from app.models.user import User
from app.models.facility import Facility
from app.services.audit_log_service import AuditLogService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/facilities", tags=["facilities"])

DEFAULT_MODULES_BY_FACILITY_TYPE = {
    "clinic": ["reception", "records", "consultations", "pharmacy", "billing"],
    "hospital": [
        "reception",
        "records",
        "consultations",
        "nursing",
        "lab",
        "pharmacy",
        "billing",
        "radiology",
        "inventory",
        "reports",
    ],
    "lab": ["reception", "records", "lab", "billing", "inventory", "reports"],
    "pharmacy": ["pharmacy", "inventory", "billing", "reports"],
}


def normalize_facility_modules(
    modules: Optional[List[str]],
    facility_type: str = "hospital",
) -> List[str]:
    raw_modules = modules or DEFAULT_MODULES_BY_FACILITY_TYPE.get(
        facility_type,
        DEFAULT_MODULES_BY_FACILITY_TYPE["hospital"],
    )
    valid_modules = set(Facility.AVAILABLE_MODULES)
    normalized: List[str] = []

    for raw_module in raw_modules:
        module = Validators.sanitize_string(str(raw_module)).lower()
        module = Facility.MODULE_ALIASES.get(module, module)
        if module not in valid_modules:
            raise HTTPException(status_code=400, detail=f"Invalid module: {raw_module}")
        if module not in normalized:
            normalized.append(module)

    if not normalized:
        raise HTTPException(status_code=400, detail="At least one module must be enabled")

    return normalized


def build_facility_response(facility: Facility) -> FacilityResponse:
    return FacilityResponse(
        id=str(facility.id),
        tenant_id=str(facility.id),
        name=facility.name,
        slug=facility.slug,
        type=facility.type,
        country=facility.country,
        address=facility.address,
        phone=facility.phone,
        email=facility.email,
        modules=normalize_facility_modules(facility.modules, facility.type),
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
        modules=normalize_facility_modules(data.modules, data.type),
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

    if user.facility_slug != facility.slug or user.facility_id != facility.id:
        user.facility_id = facility.id
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


def require_admin_for_facility(user: User, facility: Facility) -> None:
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only facility admins can manage staff")

    if user.facility_id:
        if str(user.facility_id) != str(facility.id):
            raise HTTPException(status_code=403, detail="Cannot manage another facility")
        return

    if user.facility_slug != facility.slug:
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


def next_staff_login_id(facility: Facility, role: str) -> str:
    prefix = ROLE_PREFIX[role]
    existing_count = (
        db_session.query(User)
        .filter(
            or_(User.facility_id == facility.id, User.facility_slug == facility.slug),
            User.role == role,
        )
        .count()
    )
    return f"{facility.slug}-{prefix}-{existing_count + 1:03d}"


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
        facilityId=str(user.facility_id) if user.facility_id else None,
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

    facility = None
    if current_user.facility_id:
        facility = (
            db_session.query(Facility)
            .filter_by(id=current_user.facility_id, is_active=True)
            .first()
        )
    elif current_user.facility_slug:
        facility = get_facility_or_404(current_user.facility_slug)
        current_user.facility_id = facility.id
        db_session.add(current_user)
        db_session.flush()

    if not facility:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")
    return facility


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


@router.get("/workspace/{facility_slug}", response_model=FacilityResponse)
async def get_public_facility_workspace(
    facility_slug: str,
    db: Session = Depends(get_db)
):
    """Return non-sensitive workspace metadata needed before login."""
    facility = get_facility_or_404(facility_slug)
    return build_facility_response(facility)


@router.get("/{facility_slug}/staff", response_model=List[FacilityStaffResponse])
async def get_facility_staff(
    facility_slug: str,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """List active staff accounts for a facility."""
    facility = get_facility_or_404(facility_slug)
    require_admin_for_facility(current_user, facility)

    staff = (
        db_session.query(User)
        .filter(
            or_(User.facility_id == facility.id, User.facility_slug == facility.slug),
            User.is_active == True,
        )
        .order_by(User.created_at.asc())
        .all()
    )

    return [build_staff_response(member) for member in staff]


@router.get("/{facility_slug}/clinicians", response_model=List[FacilityStaffResponse])
async def get_facility_clinicians(
    facility_slug: str,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    """List active clinicians that can be assigned to appointments."""
    facility = get_facility_or_404(facility_slug)
    if current_user.facility_id:
        if str(current_user.facility_id) != str(facility.id):
            raise HTTPException(status_code=403, detail="Cannot access another facility")
    elif current_user.facility_slug != facility.slug:
        raise HTTPException(status_code=403, detail="Cannot access another facility")

    clinicians = (
        db_session.query(User)
        .filter(
            or_(User.facility_id == facility.id, User.facility_slug == facility.slug),
            User.role.in_(["ADMIN", "DOCTOR"]),
            User.is_active == True,
        )
        .order_by(User.role.asc(), User.first_name.asc(), User.username.asc())
        .all()
    )

    return [build_staff_response(member) for member in clinicians]


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
    facility = get_facility_or_404(facility_slug)
    require_admin_for_facility(current_user, facility)

    frontend_role = data.role.lower()
    role = FRONTEND_TO_BACKEND_ROLE.get(frontend_role, data.role.upper())
    if role not in ROLE_PREFIX or role == "ADMIN":
        raise HTTPException(status_code=400, detail="Invalid staff role")

    full_name = Validators.sanitize_string(data.fullName)
    department = Validators.sanitize_string(data.department)
    first_name, last_name = split_full_name(full_name)
    login_id = next_staff_login_id(facility, role)
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
        facility_id=facility.id,
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
    facility = get_facility_or_404(facility_slug)
    require_admin_for_facility(current_user, facility)

    member = (
        db_session.query(User)
        .filter(
            or_(User.facility_id == facility.id, User.facility_slug == facility.slug),
            User.username == login_id,
            User.is_active == True,
        )
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Staff member not found")

    return build_staff_response(member)


@router.put("/{facility_slug}/staff/{login_id}", response_model=FacilityStaffResponse)
async def update_facility_staff_member(
    facility_slug: str,
    login_id: str,
    data: FacilityStaffUpdate,
    request: Request,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Update a staff account's details, role, active state, or password."""
    facility = get_facility_or_404(facility_slug)
    require_admin_for_facility(current_user, facility)

    member = (
        db_session.query(User)
        .filter(
            or_(User.facility_id == facility.id, User.facility_slug == facility.slug),
            User.username == login_id,
        )
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Staff member not found")

    payload = data.model_dump(exclude_unset=True)

    if "fullName" in payload and payload["fullName"] is not None:
        full_name = Validators.sanitize_string(payload["fullName"])
        member.first_name, member.last_name = split_full_name(full_name)

    if "role" in payload and payload["role"] is not None:
        frontend_role = payload["role"].lower()
        role = FRONTEND_TO_BACKEND_ROLE.get(frontend_role, payload["role"].upper())
        if role not in ROLE_PREFIX or role == "ADMIN":
            raise HTTPException(status_code=400, detail="Invalid staff role")
        member.role = role

    if "department" in payload and payload["department"] is not None:
        member.department = Validators.sanitize_string(payload["department"])

    if "phone" in payload:
        member.phone = Validators.sanitize_string(payload["phone"] or "—")

    if "email" in payload and payload["email"] is not None:
        email = str(payload["email"]).lower()
        existing = db_session.query(User).filter(User.email == email, User.id != member.id).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already exists")
        member.email = email

    temporary_password = ""
    if "password" in payload and payload["password"]:
        is_valid_password, password_error = Validators.validate_password(payload["password"])
        if not is_valid_password:
            raise HTTPException(status_code=400, detail=password_error)
        member.set_password(payload["password"])
        member.must_change_password = True if payload.get("mustChangePassword") is None else bool(payload["mustChangePassword"])
        temporary_password = payload["password"]
    elif "mustChangePassword" in payload:
        member.must_change_password = bool(payload["mustChangePassword"])

    if "isActive" in payload:
        if member.id == current_user.id and payload["isActive"] is False:
            raise HTTPException(status_code=400, detail="You cannot deactivate your own admin account")
        member.is_active = bool(payload["isActive"])

    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)

    AuditLogService.log_action(
        user_id=current_user.id,
        action="UPDATE_STAFF",
        resource_type="user",
        resource_id=member.id,
        facility_slug=facility.slug,
        details={
            "login_id": member.username,
            "fields": sorted(payload.keys()),
        },
        request=request,
    )

    return build_staff_response(
        member,
        temporary_password=temporary_password,
        created_by=current_user.username,
    )


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
    request: Request,
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
        request=request,
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
    request: Request,
    payload: List[str] | FacilityModulesUpdate = Body(...),
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Update enabled modules for a facility"""
    facility = get_current_admin_facility(current_user)
    if facility_id not in {facility.id, facility.slug}:
        raise HTTPException(status_code=404, detail="Facility not found")

    modules = payload.modules if isinstance(payload, FacilityModulesUpdate) else payload
    normalized_modules = normalize_facility_modules(modules, facility.type)

    facility.modules = normalized_modules
    facility.save()
    db_session.commit()

    AuditLogService.log_action(
        user_id=current_user.id,
        action="UPDATE_FACILITY_MODULES",
        resource_type="facility",
        resource_id=facility.id,
        facility_slug=facility.slug,
        details={"modules": normalized_modules},
        request=request,
    )

    return build_facility_response(facility)
