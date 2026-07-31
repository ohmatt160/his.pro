from typing import List, Optional

from pydantic import BaseModel, Field


class InventoryCreate(BaseModel):
    facility_slug: Optional[str] = Field(None)
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
    current_stock: int = Field(..., ge=0)
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


class ReorderRequest(BaseModel):
    item_ids: List[str] = Field(..., min_length=1, description="List of inventory item IDs to reorder")
    supplier_id: Optional[str] = Field(None, description="Optional supplier ID for the reorder")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes for the reorder")
