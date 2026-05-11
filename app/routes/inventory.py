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


class LowStockItemResponse(BaseModel):
    id: str
    medication_id: Optional[str]
    medication_name: Optional[str]
    quantity: int
    reorder_level: int
    facility_slug: Optional[str]


class MessageResponse(BaseModel):
    message: str


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
    query = db_session.query(Inventory).filter_by(is_active=True)

    # Facility filter
    if current_user.role != 'ADMIN' and current_user.facility_slug:
        query = query.filter_by(facility_slug=current_user.facility_slug)
    elif facility_slug:
        query = query.filter_by(facility_slug=facility_slug)

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

    # Build response
    results = []
    for item in items:
        results.append(InventoryResponse(
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
        ))

    return results


@router.post("", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
async def create_inventory_item(
    data: InventoryCreate,
    current_user: User = Depends(role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER')),
    db: Session = Depends(get_db)
):
    """Create a new inventory item"""
    # Validate required fields
    if not data.facility_slug or not data.name or not data.sku or not data.category or not data.unit:
        raise HTTPException(status_code=400, detail="Missing required fields")

    # Facility access for non-ADMIN
    if current_user.role != 'ADMIN' and current_user.facility_slug != data.facility_slug:
        raise HTTPException(status_code=403, detail="Cannot create items for other facilities")

    # Check for duplicate SKU in same facility and active
    existing = db_session.query(Inventory).filter_by(
        facility_slug=data.facility_slug,
        sku=data.sku,
        is_active=True
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="An item with this SKU already exists in this facility")

    # Validate supplier if provided
    if data.supplier_id:
        supplier = db_session.query(Supplier).filter_by(id=data.supplier_id).first()
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

    # Parse expiry_date
    expiry_date = None
    if data.expiry_date:
        try:
            expiry_date = datetime.strptime(data.expiry_date, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid expiry_date format. Use YYYY-MM-DD")

    # Create inventory item
    inventory = Inventory(
        facility_slug=data.facility_slug,
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

    return InventoryResponse(
        id=str(inventory.id),
        facility_slug=inventory.facility_slug,
        name=inventory.name,
        sku=inventory.sku,
        category=inventory.category,
        unit=inventory.unit,
        reorder_level=inventory.reorder_level or 0,
        reorder_quantity=inventory.reorder_quantity or 0,
        current_stock=inventory.current_stock or 0,
        expiry_date=inventory.expiry_date.isoformat() if inventory.expiry_date else None,
        supplier_id=str(inventory.supplier_id) if inventory.supplier_id else None,
        unit_cost=float(inventory.unit_cost) if inventory.unit_cost else 0.0,
        is_active=inventory.is_active,
        needs_reorder=inventory.needs_reorder,
        supplier_name=inventory.supplier.name if inventory.supplier else None,
        created_at=inventory.created_at.isoformat() if inventory.created_at else "",
        updated_at=inventory.updated_at.isoformat() if inventory.updated_at else None
    )


@router.get("/{item_id}", response_model=InventoryResponse)
async def get_inventory_item(
    item_id: str,
    current_user: User = Depends(role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER', 'DOCTOR', 'NURSE')),
    db: Session = Depends(get_db)
):
    """Get inventory item by ID"""
    # Filter by facility if not admin
    if current_user.role != 'ADMIN' and current_user.facility_slug:
        item = db_session.query(Inventory).filter_by(id=item_id, facility_slug=current_user.facility_slug).first()
    else:
        item = db_session.query(Inventory).filter_by(id=item_id).first()

    if not item or not item.is_active:
        raise HTTPException(status_code=404, detail="Inventory item not found")

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


@router.put("/{item_id}", response_model=InventoryResponse)
async def update_inventory_item(
    item_id: str,
    data: InventoryUpdate,
    current_user: User = Depends(role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER')),
    db: Session = Depends(get_db)
):
    """Update inventory item"""
    # Get item with facility check
    if current_user.role != 'ADMIN':
        item = db_session.query(Inventory).filter_by(id=item_id, facility_slug=current_user.facility_slug).first()
    else:
        item = db_session.query(Inventory).filter_by(id=item_id).first()

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
                raise HTTPException(status_code=400, detail="Invalid expiry_date format. Use YYYY-MM-DD")
        else:
            item.expiry_date = None

    item.save()
    db_session.commit()

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


@router.delete("/{item_id}", response_model=MessageResponse)
async def deactivate_inventory_item(
    item_id: str,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Deactivate inventory item (soft delete)"""
    item = db_session.query(Inventory).filter_by(id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    if item.current_stock > 0:
        raise HTTPException(status_code=400, detail="Cannot delete item with current stock > 0")

    item.is_active = False
    item.save()
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
    if current_user.role != 'ADMIN':
        item = db_session.query(Inventory).filter_by(id=item_id, facility_slug=current_user.facility_slug).first()
    else:
        item = db_session.query(Inventory).filter_by(id=item_id).first()

    if not item or not item.is_active:
        raise HTTPException(status_code=404, detail="Inventory item not found")

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

    item.save()
    db_session.commit()

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


@router.get("/low-stock", response_model=List[LowStockItemResponse])
async def get_low_stock(
    facility_slug: Optional[str] = Query(None),
    current_user: User = Depends(role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER')),
    db: Session = Depends(get_db)
):
    """Get items that are below reorder level"""
    query = db_session.query(Inventory).filter_by(is_active=True)

    # Facility filter
    if current_user.role != 'ADMIN' and current_user.facility_slug:
        query = query.filter_by(facility_slug=current_user.facility_slug)
    elif facility_slug:
        query = query.filter_by(facility_slug=facility_slug)

    # Items needing reorder
    query = query.filter(Inventory.current_stock <= Inventory.reorder_level)

    items = query.order_by(Inventory.current_stock).all()

    results = []
    for item in items:
        results.append(LowStockItemResponse(
            id=str(item.id),
            medication_id=str(item.id),  # using same id for now
            medication_name=item.name,
            quantity=item.current_stock or 0,
            reorder_level=item.reorder_level or 0,
            facility_slug=item.facility_slug
        ))
    return results


@router.post("/reorder", response_model=MessageResponse)
async def create_reorder_requests(
    data: ReorderRequest,
    current_user: User = Depends(role_required('ADMIN', 'PHARMACIST')),
    db: Session = Depends(get_db)
):
    """Create reorder requests for low stock items (placeholder)"""
    # In a full implementation, this would create PurchaseOrder or similar
    # For now, just return count
    count = len(data.item_ids)
    return MessageResponse(message=f"Created {count} reorder request(s)")
