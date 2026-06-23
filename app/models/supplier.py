from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel


class Supplier(BaseModel):
    """Supplier model for managing medical suppliers/vendors"""
    __tablename__ = 'suppliers'
    __table_args__ = (
        Index('idx_suppliers_facility_active', 'facility_slug', 'is_active'),
        Index('idx_suppliers_facility_name', 'facility_slug', 'name'),
    )

    facility_id = Column(String(36), ForeignKey('facilities.id'), nullable=True, index=True)
    facility_slug = Column(String(100), ForeignKey('facilities.slug'), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    contact_person = Column(String(100))
    email = Column(String(120))
    phone = Column(String(20))
    address = Column(Text)
    is_active = Column(Boolean, default=True)

    def to_dict(self):
        """Convert to dictionary"""
        data = super().to_dict()
        return data
