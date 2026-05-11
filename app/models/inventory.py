from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, String, Integer, Date, Numeric, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel


class Inventory(BaseModel):
    """Inventory model for managing medical supplies and medications"""
    __tablename__ = 'inventory'

    facility_slug = Column(String(100), ForeignKey('facilities.slug'), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    sku = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)  # medication/supplies/equipment
    unit = Column(String(50), nullable=False)  # e.g., tablet, vial, piece
    reorder_level = Column(Integer, default=0)
    reorder_quantity = Column(Integer, default=0)
    current_stock = Column(Integer, default=0)
    expiry_date = Column(Date, nullable=True)
    supplier_id = Column(String(36), ForeignKey('suppliers.id'), nullable=True)
    unit_cost = Column(Numeric(10, 2), default=Decimal('0.00'))
    is_active = Column(Boolean, default=True)

    # Relationships
    supplier = relationship('Supplier', backref='inventory_items', lazy=True)

    # Categories
    CATEGORIES = ['medication', 'supplies', 'equipment']

    def to_dict(self):
        """Convert to dictionary"""
        data = super().to_dict()
        # Convert Decimal to float for JSON serialization
        if data.get('unit_cost'):
            data['unit_cost'] = float(data['unit_cost'])
        return data

    @property
    def needs_reorder(self):
        """Check if item needs reordering"""
        return self.current_stock <= self.reorder_level
