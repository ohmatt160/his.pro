from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.extensions import db_session, get_db
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.suppliers import SupplierCreate, SupplierResponse, SupplierUpdate
from app.schemas.users import MessageResponse
from app.services.audit_log_service import AuditLogService
from app.utils.dependencies import role_required
from app.utils.validators import Validators

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


def _require_facility(current_user: User) -> str:
    if not current_user.facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")
    return current_user.facility_slug


def _supplier_response(supplier: Supplier) -> SupplierResponse:
    return SupplierResponse(
        id=str(supplier.id),
        facility_slug=supplier.facility_slug,
        name=supplier.name,
        contact_person=supplier.contact_person,
        email=supplier.email,
        phone=supplier.phone,
        address=supplier.address,
        is_active=supplier.is_active,
        created_at=supplier.created_at.isoformat() if supplier.created_at else "",
        updated_at=supplier.updated_at.isoformat() if supplier.updated_at else None,
    )


@router.get("", response_model=List[SupplierResponse])
async def get_suppliers(
    search: Optional[str] = Query(None, max_length=100),
    active_only: bool = Query(True),
    current_user: User = Depends(role_required("ADMIN", "PHARMACIST", "STORE_KEEPER")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    query = db_session.query(Supplier).filter_by(facility_slug=facility_slug)

    if active_only:
        query = query.filter_by(is_active=True)
    if search:
        query = query.filter(Supplier.name.ilike(f"%{search}%"))

    suppliers = query.order_by(Supplier.name.asc()).all()
    return [_supplier_response(supplier) for supplier in suppliers]


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    data: SupplierCreate,
    request: Request,
    current_user: User = Depends(role_required("ADMIN", "PHARMACIST", "STORE_KEEPER")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    name = Validators.sanitize_string(data.name)
    existing = db_session.query(Supplier).filter(
        Supplier.facility_slug == facility_slug,
        Supplier.name == name,
        Supplier.is_active == True,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Supplier already exists")

    supplier = Supplier(
        facility_slug=facility_slug,
        name=name,
        contact_person=Validators.sanitize_string(data.contact_person or "") or None,
        email=str(data.email).lower() if data.email else None,
        phone=Validators.sanitize_string(data.phone or "") or None,
        address=Validators.sanitize_string(data.address or "") or None,
    )
    db_session.add(supplier)
    db_session.commit()
    db_session.refresh(supplier)

    AuditLogService.log_action(
        user_id=current_user.id,
        action="CREATE_SUPPLIER",
        resource_type="supplier",
        resource_id=supplier.id,
        facility_slug=facility_slug,
        details={"name": supplier.name},
        request=request,
    )

    return _supplier_response(supplier)


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: str,
    current_user: User = Depends(role_required("ADMIN", "PHARMACIST", "STORE_KEEPER")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    supplier = db_session.query(Supplier).filter_by(
        id=supplier_id,
        facility_slug=facility_slug,
    ).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    return _supplier_response(supplier)


@router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: str,
    data: SupplierUpdate,
    request: Request,
    current_user: User = Depends(role_required("ADMIN", "PHARMACIST", "STORE_KEEPER")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    supplier = db_session.query(Supplier).filter_by(
        id=supplier_id,
        facility_slug=facility_slug,
    ).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    payload = data.model_dump(exclude_unset=True)
    if "name" in payload:
        name = Validators.sanitize_string(payload["name"])
        existing = db_session.query(Supplier).filter(
            Supplier.facility_slug == facility_slug,
            Supplier.name == name,
            Supplier.id != supplier_id,
            Supplier.is_active == True,
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Supplier already exists")
        supplier.name = name
    if "contact_person" in payload:
        supplier.contact_person = Validators.sanitize_string(payload["contact_person"] or "") or None
    if "email" in payload:
        supplier.email = str(payload["email"]).lower() if payload["email"] else None
    if "phone" in payload:
        supplier.phone = Validators.sanitize_string(payload["phone"] or "") or None
    if "address" in payload:
        supplier.address = Validators.sanitize_string(payload["address"] or "") or None
    if "is_active" in payload:
        supplier.is_active = payload["is_active"]

    supplier.save()

    AuditLogService.log_action(
        user_id=current_user.id,
        action="UPDATE_SUPPLIER",
        resource_type="supplier",
        resource_id=supplier.id,
        facility_slug=facility_slug,
        details={"fields": sorted(payload.keys())},
        request=request,
    )

    return _supplier_response(supplier)


@router.delete("/{supplier_id}", response_model=MessageResponse)
async def deactivate_supplier(
    supplier_id: str,
    request: Request,
    current_user: User = Depends(role_required("ADMIN", "PHARMACIST", "STORE_KEEPER")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    supplier = db_session.query(Supplier).filter_by(
        id=supplier_id,
        facility_slug=facility_slug,
    ).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    supplier.is_active = False
    supplier.save()

    AuditLogService.log_action(
        user_id=current_user.id,
        action="DEACTIVATE_SUPPLIER",
        resource_type="supplier",
        resource_id=supplier.id,
        facility_slug=facility_slug,
        details={"name": supplier.name},
        request=request,
    )

    return MessageResponse(message="Supplier deactivated successfully")
