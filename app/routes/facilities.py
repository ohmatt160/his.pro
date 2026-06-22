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
import uuid

from app.extensions import get_db, db_session
from app.schemas.branches import BranchCreate, BranchModulesUpdate, BranchResponse, BranchUpdate
from app.schemas.facilities import (
    DepartmentCreate,
    DepartmentUpdate,
    FacilityResponse,
    FacilityCreate,
    FacilityUpdate,
    FacilityModulesUpdate,
    FacilitySettingsUpdate,
)
from app.schemas.users import MessageResponse, FacilityStaffCreate, FacilityStaffUpdate, FacilityStaffResponse
from app.utils.dependencies import get_current_user, role_required
from app.utils.validators import Validators
from app.models.user import User
from app.models.facility import Facility
from app.models.branch import Branch
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




def build_branch_response(branch: Branch) -> BranchResponse:
    return BranchResponse(
        id=str(branch.id),
        facility_id=str(branch.facility_id),
        facility_slug=branch.facility_slug,
        name=branch.name,
        slug=branch.slug,
        location=branch.location,
        address=branch.address,
        phone=branch.phone,
        email=branch.email,
        modules=normalize_facility_modules(branch.modules, "hospital") if branch.modules else [],
        settings=branch.settings or {},
        is_public=bool(branch.is_public),
        is_active=bool(branch.is_active),
        login_url_path=f"/{branch.facility_slug}/branches/{branch.slug}/login",
        dashboard_url_path=f"/{branch.facility_slug}/branches/{branch.slug}/dashboard",
        created_at=branch.created_at.isoformat() if branch.created_at else "",
        updated_at=branch.updated_at.isoformat() if branch.updated_at else None,
    )


def branch_slug(name: str, facility_slug: str, exclude_id: str | None = None) -> str:
    base_slug = Validators.generate_slug(name)
    slug = base_slug
    suffix = 2
    query = db_session.query(Branch).filter_by(facility_slug=facility_slug)
    if exclude_id:
        query = query.filter(Branch.id != exclude_id)
    existing = {branch.slug for branch in query.all()}
    while slug in existing:
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    return slug


def sync_legacy_departments_to_branches(facility: Facility) -> list[Branch]:
    branches = (
        db_session.query(Branch)
        .filter_by(facility_slug=facility.slug, is_active=True)
        .order_by(Branch.created_at.asc())
        .all()
    )
    if branches or not facility.departments:
        return branches

    created: list[Branch] = []
    for legacy in facility.departments or []:
        name = Validators.sanitize_string(str(legacy.get("name") or ""))
        if not name:
            continue
        modules = legacy.get("modules") or legacy.get("services") or facility.modules or []
        try:
            modules = normalize_facility_modules(modules, facility.type)
        except HTTPException:
            modules = normalize_facility_modules(facility.modules, facility.type)
        branch = Branch(
            facility_id=facility.id,
            facility_slug=facility.slug,
            name=name,
            slug=legacy.get("slug") or branch_slug(name, facility.slug),
            location=legacy.get("location") or "",
            phone=legacy.get("phone_extension") or "",
            modules=modules,
            settings={"legacy_department_id": legacy.get("id")},
            is_public=bool(legacy.get("is_visible")),
        )
        db_session.add(branch)
        created.append(branch)
    if created:
        db_session.flush()
        branches = created
    return branches


def get_facility_branches(facility: Facility) -> list[Branch]:
    return sync_legacy_departments_to_branches(facility)


def get_branch_or_404(facility: Facility, branch_id_or_slug: str) -> Branch:
    branch = (
        db_session.query(Branch)
        .filter(
            Branch.facility_slug == facility.slug,
            Branch.is_active == True,
            or_(Branch.id == branch_id_or_slug, Branch.slug == branch_id_or_slug),
        )
        .first()
    )
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return branch


def require_branch_access(user: User, branch: Branch) -> None:
    if user.role == "ADMIN":
        return
    allowed = {str(user.branch_id or ""), *[str(item) for item in (user.branch_ids or [])]}
    legacy_allowed = {str(user.department_id or ""), *[str(item) for item in (user.departments or [])]}
    if str(branch.id) not in allowed and str(branch.id) not in legacy_allowed:
        raise HTTPException(status_code=403, detail="Cannot access another branch")

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
        hospital_type=facility.hospital_type or "single",
        departments=facility.departments or [],
        branches=[build_branch_response(branch) for branch in get_facility_branches(facility)],
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
        hospital_type="single",
        departments=[],
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
    "branch_admin": "BRANCH_ADMIN",
    "doctor": "DOCTOR",
    "nurse": "NURSE",
    "reception": "RECEPTIONIST",
    "pharmacist": "PHARMACIST",
    "lab": "LAB_TECH",
}

BACKEND_TO_FRONTEND_ROLE = {
    "ADMIN": "admin",
    "BRANCH_ADMIN": "branch_admin",
    "DOCTOR": "doctor",
    "NURSE": "nurse",
    "RECEPTIONIST": "reception",
    "PHARMACIST": "pharmacist",
    "LAB_TECH": "lab",
}

ROLE_PREFIX = {
    "ADMIN": "ADM",
    "BRANCH_ADMIN": "BADM",
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
    next_number = existing_count + 1
    while True:
        login_id = f"{facility.slug}-{prefix}-{next_number:03d}"
        if not db_session.query(User).filter_by(username=login_id).first():
            return login_id
        next_number += 1


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
        departmentId=user.department_id,
        departmentIds=user.departments or [],
        branchId=user.branch_id or user.department_id,
        branchIds=user.branch_ids or user.departments or [],
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


def normalize_departments(facility: Facility) -> list[dict]:
    return list(facility.departments or [])


def find_department(facility: Facility, dept_id: str) -> dict | None:
    return next((dept for dept in normalize_departments(facility) if dept.get("id") == dept_id), None)


def department_slug(name: str, departments: list[dict]) -> str:
    base_slug = Validators.generate_slug(name)
    existing = {dept.get("slug") for dept in departments}
    slug = base_slug
    suffix = 2
    while slug in existing:
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    return slug


def department_payload(data: DepartmentCreate | DepartmentUpdate, existing: dict | None = None, departments: list[dict] | None = None) -> dict:
    payload = existing.copy() if existing else {}
    incoming = data.model_dump(exclude_unset=True)
    if "name" in incoming:
        name = Validators.sanitize_string(incoming["name"])
        payload["name"] = name
        if not existing:
            payload["slug"] = department_slug(name, departments or [])
    for field in ["location", "phone_extension"]:
        if field in incoming:
            payload[field] = Validators.sanitize_string(incoming.get(field) or "")
    if "services" in incoming:
        payload["services"] = [Validators.sanitize_string(str(service)) for service in (incoming.get("services") or [])]
    if "is_visible" in incoming:
        payload["is_visible"] = bool(incoming["is_visible"])
    if not existing:
        payload["id"] = str(uuid.uuid4())
        payload.setdefault("location", "")
        payload.setdefault("phone_extension", "")
        payload.setdefault("services", [])
        payload.setdefault("is_visible", False)
    return payload


def require_department(facility: Facility, dept_id: str) -> dict:
    department = find_department(facility, dept_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    return department


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


@router.put("/{facility_slug}/settings", response_model=FacilityResponse)
async def update_facility_settings(
    facility_slug: str,
    data: FacilitySettingsUpdate,
    request: Request,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Switch a facility between single-hospital and multi-clinic operation."""
    facility = get_facility_or_404(facility_slug)
    require_admin_for_facility(current_user, facility)
    facility.hospital_type = data.hospital_type
    if data.hospital_type == "multi_clinic" and facility.departments is None:
        facility.departments = []
    facility.save()
    db_session.commit()

    AuditLogService.log_action(
        user_id=current_user.id,
        action="UPDATE_FACILITY_SETTINGS",
        resource_type="facility",
        resource_id=facility.id,
        facility_slug=facility.slug,
        details={"hospital_type": facility.hospital_type},
        request=request,
    )
    return build_facility_response(facility)




@router.get("/{facility_slug}/branches", response_model=List[BranchResponse])
async def list_branches(
    facility_slug: str,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST', 'PHARMACIST', 'LAB_TECH')),
    db: Session = Depends(get_db),
):
    facility = get_facility_or_404(facility_slug)
    if current_user.facility_slug != facility.slug and str(current_user.facility_id or "") != str(facility.id):
        raise HTTPException(status_code=403, detail="Cannot access another facility")
    branches = get_facility_branches(facility)
    if current_user.role == "ADMIN":
        return [build_branch_response(branch) for branch in branches]
    allowed = {str(current_user.branch_id or current_user.department_id or "")}
    allowed.update(str(item) for item in (current_user.branch_ids or current_user.departments or []))
    return [build_branch_response(branch) for branch in branches if str(branch.id) in allowed]


@router.post("/{facility_slug}/branches", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
async def create_branch(
    facility_slug: str,
    data: BranchCreate,
    request: Request,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db),
):
    facility = get_facility_or_404(facility_slug)
    require_admin_for_facility(current_user, facility)
    name = Validators.sanitize_string(data.name)
    branch = Branch(
        facility_id=facility.id,
        facility_slug=facility.slug,
        name=name,
        slug=branch_slug(name, facility.slug),
        location=Validators.sanitize_string(data.location or ""),
        address=Validators.sanitize_string(data.address or ""),
        phone=Validators.sanitize_string(data.phone or ""),
        email=str(data.email).lower() if data.email else "",
        modules=[],
        settings=data.settings or {},
    )
    db_session.add(branch)
    if facility.hospital_type != "multi_clinic":
        facility.hospital_type = "multi_clinic"
        db_session.add(facility)
    db_session.commit()
    db_session.refresh(branch)
    AuditLogService.log_action(
        user_id=current_user.id,
        action="CREATE_BRANCH",
        resource_type="branch",
        resource_id=branch.id,
        facility_slug=facility.slug,
        details={"name": branch.name, "modules": branch.modules},
        request=request,
    )
    return build_branch_response(branch)


@router.put("/{facility_slug}/branches/{branch_id_or_slug}", response_model=BranchResponse)
async def update_branch(
    facility_slug: str,
    branch_id_or_slug: str,
    data: BranchUpdate,
    request: Request,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN')),
    db: Session = Depends(get_db),
):
    facility = get_facility_or_404(facility_slug)
    branch = get_branch_or_404(facility, branch_id_or_slug)
    if current_user.role == "ADMIN":
        require_admin_for_facility(current_user, facility)
    else:
        require_branch_access(current_user, branch)
    payload = data.model_dump(exclude_unset=True)
    if "name" in payload and payload["name"]:
        branch.name = Validators.sanitize_string(payload["name"])
        branch.slug = branch_slug(branch.name, facility.slug, exclude_id=branch.id)
    for field in ("location", "address", "phone"):
        if field in payload:
            setattr(branch, field, Validators.sanitize_string(payload.get(field) or ""))
    if "email" in payload:
        branch.email = str(payload["email"]).lower() if payload["email"] else ""
    if "modules" in payload and payload["modules"] is not None:
        branch.modules = normalize_facility_modules(payload["modules"], facility.type) if payload["modules"] else []
    if "settings" in payload and payload["settings"] is not None:
        branch.settings = payload["settings"]
    if "is_public" in payload:
        branch.is_public = bool(payload["is_public"])
    if "is_active" in payload and current_user.role == "ADMIN":
        branch.is_active = bool(payload["is_active"])
    db_session.add(branch)
    db_session.commit()
    db_session.refresh(branch)
    AuditLogService.log_action(
        user_id=current_user.id,
        action="UPDATE_BRANCH",
        resource_type="branch",
        resource_id=branch.id,
        facility_slug=facility.slug,
        details={"fields": sorted(payload.keys())},
        request=request,
    )
    return build_branch_response(branch)


@router.put("/{facility_slug}/branches/{branch_id_or_slug}/modules", response_model=BranchResponse)
async def update_branch_modules(
    facility_slug: str,
    branch_id_or_slug: str,
    data: BranchModulesUpdate,
    request: Request,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN')),
    db: Session = Depends(get_db),
):
    facility = get_facility_or_404(facility_slug)
    branch = get_branch_or_404(facility, branch_id_or_slug)
    if current_user.role == "ADMIN":
        require_admin_for_facility(current_user, facility)
    else:
        require_branch_access(current_user, branch)
    branch.modules = normalize_facility_modules(data.modules, facility.type) if data.modules else []
    db_session.add(branch)
    db_session.commit()
    db_session.refresh(branch)
    AuditLogService.log_action(
        user_id=current_user.id,
        action="UPDATE_BRANCH_MODULES",
        resource_type="branch",
        resource_id=branch.id,
        facility_slug=facility.slug,
        details={"modules": branch.modules},
        request=request,
    )
    return build_branch_response(branch)


@router.delete("/{facility_slug}/branches/{branch_id_or_slug}", response_model=MessageResponse)
async def deactivate_branch(
    facility_slug: str,
    branch_id_or_slug: str,
    request: Request,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db),
):
    facility = get_facility_or_404(facility_slug)
    require_admin_for_facility(current_user, facility)
    branch = get_branch_or_404(facility, branch_id_or_slug)
    assigned_staff = (
        db_session.query(User)
        .filter(
            or_(User.facility_id == facility.id, User.facility_slug == facility.slug),
            User.is_active == True,
            or_(User.branch_id == branch.id, User.department_id == branch.id),
        )
        .count()
    )
    if assigned_staff:
        raise HTTPException(status_code=400, detail="Cannot remove a branch with active staff assigned")
    branch.is_active = False
    db_session.add(branch)
    db_session.commit()
    AuditLogService.log_action(
        user_id=current_user.id,
        action="DEACTIVATE_BRANCH",
        resource_type="branch",
        resource_id=branch.id,
        facility_slug=facility.slug,
        details={},
        request=request,
    )
    return MessageResponse(message="Branch removed successfully")


@router.get("/{facility_slug}/departments")
async def list_departments(
    facility_slug: str,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST', 'PHARMACIST', 'LAB_TECH')),
    db: Session = Depends(get_db)
):
    facility = get_facility_or_404(facility_slug)
    if current_user.facility_slug != facility.slug and str(current_user.facility_id or "") != str(facility.id):
        raise HTTPException(status_code=403, detail="Cannot access another facility")
    return normalize_departments(facility)


@router.post("/{facility_slug}/departments", status_code=status.HTTP_201_CREATED)
async def add_department(
    facility_slug: str,
    data: DepartmentCreate,
    request: Request,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    facility = get_facility_or_404(facility_slug)
    require_admin_for_facility(current_user, facility)
    departments = normalize_departments(facility)
    department = department_payload(data, departments=departments)
    facility.departments = departments + [department]
    if facility.hospital_type != "multi_clinic":
        facility.hospital_type = "multi_clinic"
    facility.save()
    db_session.commit()

    AuditLogService.log_action(
        user_id=current_user.id,
        action="CREATE_DEPARTMENT",
        resource_type="department",
        resource_id=department["id"],
        facility_slug=facility.slug,
        details={"name": department["name"]},
        request=request,
    )
    return department


@router.put("/{facility_slug}/departments/{dept_id}")
async def update_department(
    facility_slug: str,
    dept_id: str,
    data: DepartmentUpdate,
    request: Request,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    facility = get_facility_or_404(facility_slug)
    require_admin_for_facility(current_user, facility)
    departments = normalize_departments(facility)
    existing = require_department(facility, dept_id)
    updated = department_payload(data, existing=existing, departments=departments)
    facility.departments = [updated if dept.get("id") == dept_id else dept for dept in departments]
    facility.save()
    db_session.commit()

    AuditLogService.log_action(
        user_id=current_user.id,
        action="UPDATE_DEPARTMENT",
        resource_type="department",
        resource_id=dept_id,
        facility_slug=facility.slug,
        details={"fields": sorted(data.model_dump(exclude_unset=True).keys())},
        request=request,
    )
    return updated


@router.delete("/{facility_slug}/departments/{dept_id}", response_model=MessageResponse)
async def remove_department(
    facility_slug: str,
    dept_id: str,
    request: Request,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    facility = get_facility_or_404(facility_slug)
    require_admin_for_facility(current_user, facility)
    require_department(facility, dept_id)
    staff = (
        db_session.query(User)
        .filter(
            or_(User.facility_id == facility.id, User.facility_slug == facility.slug),
            User.is_active == True,
        )
        .all()
    )
    assigned = [
        member for member in staff
        if member.department_id == dept_id or dept_id in (member.departments or [])
    ]
    if assigned:
        raise HTTPException(status_code=400, detail="Cannot remove a department with active staff assigned")

    facility.departments = [dept for dept in normalize_departments(facility) if dept.get("id") != dept_id]
    facility.save()
    db_session.commit()

    AuditLogService.log_action(
        user_id=current_user.id,
        action="DELETE_DEPARTMENT",
        resource_type="department",
        resource_id=dept_id,
        facility_slug=facility.slug,
        details={},
        request=request,
    )
    return MessageResponse(message="Department removed successfully")


@router.get("/{facility_slug}/staff", response_model=List[FacilityStaffResponse])
async def get_facility_staff(
    facility_slug: str,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN')),
    db: Session = Depends(get_db)
):
    """List active staff accounts for a facility."""
    facility = get_facility_or_404(facility_slug)
    if current_user.role == 'ADMIN':
        require_admin_for_facility(current_user, facility)
    elif current_user.facility_slug != facility.slug and str(current_user.facility_id or '') != str(facility.id):
        raise HTTPException(status_code=403, detail='Cannot access another facility')

    query = (
        db_session.query(User)
        .filter(
            or_(User.facility_id == facility.id, User.facility_slug == facility.slug),
            User.is_active == True,
        )
    )
    if current_user.role == 'BRANCH_ADMIN':
        branch_id = current_user.branch_id or current_user.department_id
        query = query.filter(or_(User.branch_id == branch_id, User.department_id == branch_id))

    staff = query.order_by(User.created_at.asc()).all()

    return [build_staff_response(member) for member in staff]


@router.get("/{facility_slug}/clinicians", response_model=List[FacilityStaffResponse])
async def get_facility_clinicians(
    facility_slug: str,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'RECEPTIONIST')),
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
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN')),
    db: Session = Depends(get_db)
):
    """Create a staff user for a facility and return one-time credentials."""
    facility = get_facility_or_404(facility_slug)
    if current_user.role == 'ADMIN':
        require_admin_for_facility(current_user, facility)
    elif current_user.facility_slug != facility.slug and str(current_user.facility_id or '') != str(facility.id):
        raise HTTPException(status_code=403, detail='Cannot access another facility')

    frontend_role = data.role.lower()
    role = FRONTEND_TO_BACKEND_ROLE.get(frontend_role, data.role.upper())
    if role not in ROLE_PREFIX or role == "ADMIN":
        raise HTTPException(status_code=400, detail="Invalid staff role")
    if current_user.role == 'BRANCH_ADMIN' and role == 'BRANCH_ADMIN':
        raise HTTPException(status_code=403, detail="Branch admins cannot create other branch admins")

    full_name = Validators.sanitize_string(data.fullName)
    department = Validators.sanitize_string(data.department)
    branch_id = data.branchId or data.departmentId
    branch_ids = data.branchIds or data.departmentIds or ([branch_id] if branch_id else [])
    if current_user.role == 'BRANCH_ADMIN':
        branch_id = current_user.branch_id or current_user.department_id
        branch_ids = [branch_id] if branch_id else []
    if role == "BRANCH_ADMIN" and not branch_id:
        raise HTTPException(status_code=400, detail="Select a branch before creating a branch admin")
    if branch_id:
        get_branch_or_404(facility, branch_id)
    for assigned_branch_id in branch_ids:
        get_branch_or_404(facility, assigned_branch_id)
    department_id = branch_id
    department_ids = branch_ids
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
        department_id=department_id,
        departments=department_ids,
        branch_id=branch_id,
        branch_ids=branch_ids,
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
    if current_user.role == 'ADMIN':
        require_admin_for_facility(current_user, facility)
    elif current_user.facility_slug != facility.slug and str(current_user.facility_id or '') != str(facility.id):
        raise HTTPException(status_code=403, detail='Cannot access another facility')

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
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN')),
    db: Session = Depends(get_db)
):
    """Update a staff account's details, role, active state, or password."""
    facility = get_facility_or_404(facility_slug)
    if current_user.role == 'ADMIN':
        require_admin_for_facility(current_user, facility)
    elif current_user.facility_slug != facility.slug and str(current_user.facility_id or '') != str(facility.id):
        raise HTTPException(status_code=403, detail='Cannot access another facility')

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
    if current_user.role == 'BRANCH_ADMIN':
        branch_id = current_user.branch_id or current_user.department_id
        if (member.branch_id or member.department_id) != branch_id:
            raise HTTPException(status_code=403, detail="Branch admins can only update staff assigned to their branch")

    payload = data.model_dump(exclude_unset=True)

    if "fullName" in payload and payload["fullName"] is not None:
        full_name = Validators.sanitize_string(payload["fullName"])
        member.first_name, member.last_name = split_full_name(full_name)

    if "role" in payload and payload["role"] is not None:
        frontend_role = payload["role"].lower()
        role = FRONTEND_TO_BACKEND_ROLE.get(frontend_role, payload["role"].upper())
        if role not in ROLE_PREFIX or role == "ADMIN":
            raise HTTPException(status_code=400, detail="Invalid staff role")
        if current_user.role == 'BRANCH_ADMIN' and role == 'BRANCH_ADMIN':
            raise HTTPException(status_code=403, detail="Branch admins cannot assign branch admin role")
        member.role = role

    if "department" in payload and payload["department"] is not None:
        member.department = Validators.sanitize_string(payload["department"])

    if "branchId" in payload or "departmentId" in payload:
        branch_id = payload.get("branchId", payload.get("departmentId"))
        if current_user.role == 'BRANCH_ADMIN':
            branch_id = current_user.branch_id or current_user.department_id
        if branch_id:
            get_branch_or_404(facility, branch_id)
        member.branch_id = branch_id
        member.department_id = branch_id
        if payload.get("branchIds") is None and payload.get("departmentIds") is None:
            member.branch_ids = [branch_id] if branch_id else []
            member.departments = [branch_id] if branch_id else []

    if "branchIds" in payload or ("departmentIds" in payload and payload["departmentIds"] is not None):
        branch_ids = payload.get("branchIds", payload.get("departmentIds") or [])
        for assigned_branch_id in branch_ids:
            get_branch_or_404(facility, assigned_branch_id)
        member.branch_ids = branch_ids
        member.departments = branch_ids

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
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN')),
    db: Session = Depends(get_db)
):
    """Get facility by ID or slug for the current facility context."""
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

    if current_user.facility_id:
        if str(current_user.facility_id) != str(facility.id):
            raise HTTPException(status_code=404, detail="Facility not found")
    elif current_user.facility_slug != facility.slug:
        raise HTTPException(status_code=404, detail="Facility not found")

    if facility_id not in {str(facility.id), facility.slug}:
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

