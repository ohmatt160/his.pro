"""
Inventory Routes - FastAPI Version
Converted from Flask-RESTx inventory_resource.py
"""

from fastapi import APIRouter, Depends, Header, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
import logging

from app.extensions import get_db, db_session
from app.schemas.inventory import InventoryResponse, InventoryCreate, InventoryUpdate, StockUpdate, \
    LowStockItemResponse, ReorderRequest
from app.schemas.users import MessageResponse
from app.utils.dependencies import get_current_user, role_required
from app.utils.validators import Validators
from app.models.user import User
from app.models.inventory import Inventory
from app.models.supplier import Supplier
from app.services.realtime_service import publish_tenant_event
from app.services.write_idempotency_service import WriteIdempotencyService
from app.utils.idempotency import IdempotencyConflictError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/inventory", tags=["inventory"])


def _require_facility(current_user: User) -> str:
    if not current_user.facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")
    return current_user.facility_slug


def _parse_expiry_date(value: Optional[str]):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid expiry_date format. Use YYYY-MM-DD")


def _inventory_response(item: Inventory) -> InventoryResponse:
    return InventoryResponse(
        id=str(item.id),
        facility_slug=item.facility_slug,
        name=item.name,
        sku=item.sku,
        category=item.category,
        unit=item.unit,
        reorder_level=item.reorder_level or 0,
        reorder_quantity=item.reorder_quantity or 0,
        current_stock=item.current_stock or 0,
        expiry_date=item.expiry_date.isoformat() if item.expiry_date else None,
        supplier_id=str(item.supplier_id) if item.supplier_id else None,
        unit_cost=float(item.unit_cost) if item.unit_cost else 0.0,
        is_active=item.is_active,
        needs_reorder=item.needs_reorder,
        supplier_name=item.supplier.name if item.supplier else None,
        created_at=item.created_at.isoformat() if item.created_at else "",
        updated_at=item.updated_at.isoformat() if item.updated_at else None
    )


def _publish_inventory_event(event_type: str, item: Inventory) -> None:
    publish_tenant_event(
        event_type=event_type,
        facility_slug=item.facility_slug,
        roles=["ADMIN", "BRANCH_ADMIN", "PHARMACIST", "STORE_KEEPER", "DOCTOR", "NURSE"],
        modules=["inventory"],
        resource_id=item.id,
        payload={"sku": item.sku, "current_stock": item.current_stock},
    )


@router.get("", response_model=List[InventoryResponse])
async def get_inventory_items(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    facility_slug: Optional[str] = Query(None),
    category: Optional[str] = Query(None, pattern="^(medication|supplies|equipment)$"),
    search: Optional[str] = Query(None, max_length=100),
    current_user: User = Depends(role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER', 'DOCTOR', 'NURSE')),
    db: Session = Depends(get_db)
):
    """Paginated list of inventory items"""
    facility = _require_facility(current_user)
    query = (
        db_session.query(Inventory)
        .options(joinedload(Inventory.supplier))
        .filter_by(is_active=True, facility_slug=facility)
    )

    # Category filter
    if category:
        query = query.filter_by(category=category)

    # Search filter
    if search:
        query = query.filter(
            Inventory.name.ilike(f'%{search}%') |
            Inventory.sku.ilike(f'%{search}%')
        )

    # Order
    query = query.order_by(Inventory.name)

    # Pagination
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page

    return [_inventory_response(item) for item in items]


@router.post("", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
async def create_inventory_item(
    data: InventoryCreate,
    current_user: User = Depends(role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER')),
    db: Session = Depends(get_db)
):
    """Create a new inventory item"""
    facility = _require_facility(current_user)

    if not data.name or not data.sku or not data.category or not data.unit:
        raise HTTPException(status_code=400, detail="Missing required fields")

    # Check for duplicate SKU in same facility and active
    existing = db_session.query(Inventory).filter_by(
        facility_slug=facility,
        sku=data.sku,
        is_active=True
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="An item with this SKU already exists in this facility")

    # Validate supplier if provided
    if data.supplier_id:
        supplier = db_session.query(Supplier).filter_by(
            id=data.supplier_id,
            facility_slug=facility,
            is_active=True,
        ).first()
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

    expiry_date = _parse_expiry_date(data.expiry_date)

    # Create inventory item
    inventory = Inventory(
        facility_slug=facility,
        name=data.name,
        sku=data.sku,
        category=data.category,
        unit=data.unit,
        reorder_level=data.reorder_level or 0,
        reorder_quantity=data.reorder_quantity or 0,
        current_stock=data.current_stock or 0,
        expiry_date=expiry_date,
        supplier_id=data.supplier_id,
        unit_cost=Decimal(str(data.unit_cost or 0))
    )
    inventory.save()
    _publish_inventory_event("inventory.item_created", inventory)

    return _inventory_response(inventory)


@router.get("/low-stock", response_model=List[LowStockItemResponse])
async def get_low_stock(
    facility_slug: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    current_user: User = Depends(role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER')),
    db: Session = Depends(get_db)
):
    """Get items that are below reorder level"""
    facility = _require_facility(current_user)
    items = db_session.query(Inventory).filter(
        Inventory.is_active == True,
        Inventory.facility_slug == facility,
        Inventory.current_stock <= Inventory.reorder_level,
    ).order_by(Inventory.current_stock).offset((page - 1) * per_page).limit(per_page).all()

    return [
        LowStockItemResponse(
            id=str(item.id),
            medication_id=str(item.id),
            medication_name=item.name,
            quantity=item.current_stock or 0,
            reorder_level=item.reorder_level or 0,
            facility_slug=item.facility_slug
        )
        for item in items
    ]


@router.post("/reorder", response_model=MessageResponse)
async def create_reorder_requests(
    data: ReorderRequest,
    current_user: User = Depends(role_required('ADMIN', 'PHARMACIST')),
    db: Session = Depends(get_db)
):
    """Create reorder requests for low stock items (placeholder)"""
    facility = _require_facility(current_user)
    items = db_session.query(Inventory).filter(
        Inventory.id.in_(data.item_ids),
        Inventory.facility_slug == facility,
        Inventory.is_active == True
    ).all()

    if not items:
        raise HTTPException(status_code=404, detail="No valid inventory items found")

    return MessageResponse(message=f"Created {len(items)} reorder request(s)")


@router.get("/{item_id}", response_model=InventoryResponse)
async def get_inventory_item(
    item_id: str,
    current_user: User = Depends(role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER', 'DOCTOR', 'NURSE')),
    db: Session = Depends(get_db)
):
    """Get inventory item by ID"""
    facility = _require_facility(current_user)
    item = db_session.query(Inventory).filter_by(id=item_id, facility_slug=facility).first()

    if not item or not item.is_active:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    return _inventory_response(item)


@router.put("/{item_id}", response_model=InventoryResponse)
async def update_inventory_item(
    item_id: str,
    data: InventoryUpdate,
    current_user: User = Depends(role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER')),
    db: Session = Depends(get_db)
):
    """Update inventory item"""
    facility = _require_facility(current_user)
    item = db_session.query(Inventory).filter_by(id=item_id, facility_slug=facility).first()

    if not item or not item.is_active:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    # Update fields with validation
    if data.name is not None:
        item.name = Validators.sanitize_string(data.name)
    if data.sku is not None:
        # Check for duplicate SKU in same facility (excluding self)
        existing = db_session.query(Inventory).filter(
            Inventory.facility_slug == item.facility_slug,
            Inventory.sku == data.sku,
            Inventory.is_active == True,
            Inventory.id != item_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="An item with this SKU already exists in this facility")
        item.sku = Validators.sanitize_string(data.sku)
    if data.category is not None:
        if data.category not in Inventory.CATEGORIES:
            raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(Inventory.CATEGORIES)}")
        item.category = data.category
    if data.unit is not None:
        item.unit = data.unit
    if data.reorder_level is not None:
        item.reorder_level = data.reorder_level
    if data.reorder_quantity is not None:
        item.reorder_quantity = data.reorder_quantity
    if data.supplier_id is not None:
        if data.supplier_id:
            supplier = db_session.query(Supplier).filter_by(
                id=data.supplier_id,
                facility_slug=facility,
                is_active=True,
            ).first()
            if not supplier:
                raise HTTPException(status_code=404, detail="Supplier not found")
        item.supplier_id = data.supplier_id
    if data.unit_cost is not None:
        item.unit_cost = Decimal(str(data.unit_cost))
    if data.expiry_date is not None:
        if data.expiry_date:
            try:
                item.expiry_date = _parse_expiry_date(data.expiry_date)
            except HTTPException:
                raise
        else:
            item.expiry_date = None

    item.save()
    db_session.commit()
    _publish_inventory_event("inventory.item_updated", item)

    return _inventory_response(item)


@router.delete("/{item_id}", response_model=MessageResponse)
async def deactivate_inventory_item(
    item_id: str,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Deactivate inventory item (soft delete)"""
    facility = _require_facility(current_user)
    item = db_session.query(Inventory).filter_by(id=item_id, facility_slug=facility).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    if item.current_stock > 0:
        raise HTTPException(status_code=400, detail="Cannot delete item with current stock > 0")

    item.is_active = False
    item.save()
    db_session.commit()
    _publish_inventory_event("inventory.item_deleted", item)

    return MessageResponse(message="Inventory item deactivated successfully")


@router.put("/{item_id}/stock", response_model=InventoryResponse)
async def update_stock(
    item_id: str,
    data: StockUpdate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER')),
    db: Session = Depends(get_db)
):
    """Update stock level"""
    facility = _require_facility(current_user)
    try:
        claim = WriteIdempotencyService.claim(
            facility_slug=facility,
            facility_id=current_user.facility_id,
            actor_id=current_user.id,
            operation="inventory.stock.update",
            idempotency_key=idempotency_key,
            payload={"item_id": item_id, **data.model_dump()},
        )
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    item = (
        db_session.query(Inventory)
        .filter_by(id=item_id, facility_slug=facility)
        .with_for_update()
        .first()
    )

    if not item or not item.is_active:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    if claim.replay:
        if claim.record.resource_id != str(item.id):
            raise HTTPException(status_code=409, detail="Idempotency replay target mismatch")
        return _inventory_response(item)

    adjustment_type = data.adjustment_type
    new_stock = data.current_stock

    if adjustment_type == 'set':
        item.current_stock = new_stock
    elif adjustment_type == 'addition':
        item.current_stock += new_stock
    elif adjustment_type == 'reduction':
        if item.current_stock < new_stock:
            raise HTTPException(status_code=400, detail="Insufficient stock for reduction")
        item.current_stock -= new_stock

    db_session.add(item)
    WriteIdempotencyService.complete(
        claim.record,
        resource_type="inventory",
        resource_id=item.id,
        response_status=status.HTTP_200_OK,
    )
    db_session.commit()
    db_session.refresh(item)
    _publish_inventory_event("inventory.stock_updated", item)

    return _inventory_response(item)
