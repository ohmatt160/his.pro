"""
Inventory Routes - FastAPI Version
Converted from Flask-RESTx inventory_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
import logging

from app.extensions import get_db, db_session
from app.utils.dependencies import get_current_user, role_required
from app.utils.validators import Validators
from app.models.user import User
from app.models.inventory import Inventory
from app.models.supplier import Supplier

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/inventory", tags=["inventory"])


# Pydantic Models
class InventoryCreate(BaseModel):
    facility_slug: str = Field(...)
    name: str = Field(..., max_length=200)
    sku: str = Field(..., max_length=100)
    category: str = Field(..., pattern="^(medication|supplies|equipment)$")
    unit: str = Field(..., max_length=50)
    reorder_level: Optional[int] = Field(0, ge=0)
    reorder_quantity: Optional[int] = Field(0, ge=0)
    current_stock: Optional[int] = Field(0, ge=0)
    expiry_date: Optional[str] = Field(None)
    supplier_id: Optional[str] = Field(None)
    unit_cost: Optional[float] = Field(0.0, ge=0)


class InventoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    sku: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, pattern="^(medication|supplies|equipment)$")
    unit: Optional[str] = Field(None, max_length=50)
    reorder_level: Optional[int] = Field(None, ge=0)
    reorder_quantity: Optional[int] = Field(None, ge=0)
    supplier_id: Optional[str] = Field(None)
    unit_cost: Optional[float] = Field(None, ge=0)
    expiry_date: Optional[str] = Field(None)


class StockUpdate(BaseModel):
    current_stock: int = Field(...)
    adjustment_type: str = Field(..., pattern="^(set|addition|reduction)$")


class InventoryResponse(BaseModel):
    id: str
    facility_slug: str
    name: str
    sku: str
    category: str
    unit: str
    reorder_level: int
    reorder_quantity: int
    current_stock: int
    expiry_date: Optional[str]
    supplier_id: Optional[str]
    unit_cost: float
    is_active: bool
    needs_reorder: bool
    supplier_name: Optional[str]
    created_at: str
    updated_at: Optional[str]


class InventoryListResponse(BaseModel):
    inventory_items: List[InventoryResponse]
    total: int
    page: int
    per_page: int
    pages: int


class LowStockResponse(BaseModel):
    low_stock_items: List[InventoryResponse]
    total: int


class MessageResponse(BaseModel):
    message: str


# Helper function to build response
def build_inventory_response(item):
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


@router.get("", response_model=InventoryListResponse)
async def list_inventory(
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
        facility_slug: Optional[str] = Query(None),
        category: Optional[str] = Query(None),
        search: Optional[str] = Query(None),
        current_user: User = Depends(role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER', 'DOCTOR', 'NURSE')),
        db: Session = Depends(get_db)
):
    """Get paginated list of inventory items"""
    query = db_session.query(Inventory).filter_by(is_active=True)

    if current_user.role != 'ADMIN' and current_user.facility_slug:
        query = query.filter_by(facility_slug=current_user.facility_slug)
    elif facility_slug:
        query = query.filter_by(facility_slug=facility_slug)

    if category:
        query = query.filter_by(category=category)

    if search:
        from sqlalchemy import or_
        query = query.filter(
            or_(
                Inventory.name.ilike(f'%{search}%'),
                Inventory.sku.ilike(f'%{search}%')
            )
        )

    query = query.order_by(Inventory.name)

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page

    return InventoryListResponse(
        inventory_items=[build_inventory_response(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.post("", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
async def create_inventory(
        data: InventoryCreate,
        current_user: User = Depends(role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER')),
        db: Session = Depends(get_db)
):
    """Add a new inventory item"""
    if current_user.role != 'ADMIN' and current_user.facility_slug != data.facility_slug:
        raise HTTPException(status_code=403, detail="Cannot create items for other facilities")

    existing = db_session.query(Inventory).filter_by(
        facility_slug=data.facility_slug,
        sku=data.sku,
        is_active=True
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="An item with this SKU already exists in this facility")

    if data.supplier_id:
        supplier = db_session.query(Supplier).filter_by(id=data.supplier_id).first()
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

    expiry_date = None
    if data.expiry_date:
        try:
            expiry_date = datetime.strptime(data.expiry_date, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid expiry_date format. Use YYYY-MM-DD")

    inventory = Inventory(
        facility_slug=data.facility_slug,
        name=Validators.sanitize_string(data.name),
        sku=Validators.sanitize_string(data.sku),
        category=data.category,
        unit=data.unit,
        reorder_level=data.reorder_level or 0,
        reorder_quantity=data.reorder_quantity or 0,
        current_stock=data.current_stock or 0,
        expiry_date=expiry_date,
        supplier_id=data.supplier_id,
        unit_cost=Decimal(str(data.unit_cost or 0))
    )

    db_session.add(inventory)
    db_session.commit()
    db_session.refresh(inventory)

    return build_inventory_response(inventory)


@router.get("/low-stock", response_model=LowStockResponse)
async def get_low_stock(
        facility_slug: Optional[str] = Query(None),
        current_user: User = Depends(role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER')),
        db: Session = Depends(get_db)
):
    """Get items below reorder level"""
    query = db_session.query(Inventory).filter_by(is_active=True)

    if current_user.role != 'ADMIN' and current_user.facility_slug:
        query = query.filter_by(facility_slug=current_user.facility_slug)
    elif facility_slug:
        query = query.filter_by(facility_slug=facility_slug)

    query = query.filter(Inventory.current_stock <= Inventory.reorder_level)
    items = query.order_by(Inventory.current_stock).all()

    return LowStockResponse(
        low_stock_items=[build_inventory_response(item) for item in items],
        total=len(items)
    )


@router.get("/{item_id}", response_model=InventoryResponse)
async def get_inventory(
        item_id: str,
        current_user: User = Depends(role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER', 'DOCTOR', 'NURSE')),
        db: Session = Depends(get_db)
):
    """Get inventory item by ID"""
    query = db_session.query(Inventory).filter_by(id=item_id)

    if current_user.role != 'ADMIN' and current_user.facility_slug:
        query = query.filter_by(facility_slug=current_user.facility_slug)

    item = query.first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    return build_inventory_response(item)


@router.put("/{item_id}", response_model=InventoryResponse)
async def update_inventory(
        item_id: str,
        data: InventoryUpdate,
        current_user: User = Depends(role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER')),
        db: Session = Depends(get_db)
):
    """Update inventory item"""
    query = db_session.query(Inventory).filter_by(id=item_id)

    if current_user.role != 'ADMIN' and current_user.facility_slug:
        query = query.filter_by(facility_slug=current_user.facility_slug)

    item = query.first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    if data.name is not None:
        item.name = Validators.sanitize_string(data.name)
    if data.sku is not None:
        existing = db_session.query(Inventory).filter(
            Inventory.facility_slug == item.facility_slug,
            Inventory.sku == data.sku,
            Inventory.id != item_id,
            Inventory.is_active == True
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="An item with this SKU already exists")
        item.sku = Validators.sanitize_string(data.sku)
    if data.category is not None:
        item.category = data.category
    if data.unit is not None:
        item.unit = data.unit
    if data.reorder_level is not None:
        item.reorder_level = data.reorder_level
    if data.reorder_quantity is not None:
        item.reorder_quantity = data.reorder_quantity
    if data.supplier_id is not None:
        if data.supplier_id:
            supplier = db_session.query(Supplier).filter_by(id=data.supplier_id).first()
            if not supplier:
                raise HTTPException(status_code=404, detail="Supplier not found")
        item.supplier_id = data.supplier_id
    if data.unit_cost is not None:
        item.unit_cost = Decimal(str(data.unit_cost))
    if data.expiry_date is not None:
        if data.expiry_date:
            try:
                item.expiry_date = datetime.strptime(data.expiry_date, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid expiry_date format")
        else:
            item.expiry_date = None

    db_session.commit()
    db_session.refresh(item)

    return build_inventory_response(item)


@router.delete("/{item_id}", response_model=MessageResponse)
async def delete_inventory(
        item_id: str,
        current_user: User = Depends(role_required('ADMIN')),
        db: Session = Depends(get_db)
):
    """Deactivate inventory item"""
    query = db_session.query(Inventory).filter_by(id=item_id)

    if current_user.role != 'ADMIN' and current_user.facility_slug:
        query = query.filter_by(facility_slug=current_user.facility_slug)

    item = query.first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    if item.current_stock > 0:
        raise HTTPException(status_code=400, detail="Cannot delete item with current stock")

    item.is_active = False
    db_session.commit()

    return MessageResponse(message="Inventory item deactivated successfully")


@router.put("/{item_id}/stock", response_model=InventoryResponse)
async def update_stock(
        item_id: str,
        data: StockUpdate,
        current_user: User = Depends(role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER')),
        db: Session = Depends(get_db)
):
    """Update stock level"""
    query = db_session.query(Inventory).filter_by(id=item_id)

    if current_user.role != 'ADMIN' and current_user.facility_slug:
        query = query.filter_by(facility_slug=current_user.facility_slug)

    item = query.first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    if data.adjustment_type == 'set':
        item.current_stock = data.current_stock
    elif data.adjustment_type == 'addition':
        item.current_stock += data.current_stock
    elif data.adjustment_type == 'reduction':
        if item.current_stock < data.current_stock:
            raise HTTPException(status_code=400, detail="Insufficient stock for reduction")
        item.current_stock -= data.current_stock

    db_session.commit()
    db_session.refresh(item)

    return build_inventory_response(item)