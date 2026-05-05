from datetime import datetime
from decimal import Decimal
from app.extensions import db
from app.models.base_model import BaseModel

class Inventory(BaseModel):
    """Inventory model for managing medical supplies and medications"""
    __tablename__ = 'inventory'
    
    facility_slug = db.Column(db.String(100), db.ForeignKey('facilities.slug'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # medication/supplies/equipment
    unit = db.Column(db.String(50), nullable=False)  # e.g., tablet, vial, piece
    reorder_level = db.Column(db.Integer, default=0)
    reorder_quantity = db.Column(db.Integer, default=0)
    current_stock = db.Column(db.Integer, default=0)
    expiry_date = db.Column(db.Date, nullable=True)
    supplier_id = db.Column(db.String(36), db.ForeignKey('suppliers.id'), nullable=True)
    unit_cost = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    supplier = db.relationship('Supplier', backref='inventory_items', lazy=True)
    
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