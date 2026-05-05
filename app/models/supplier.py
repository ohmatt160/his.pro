from app.extensions import db
from app.models.base_model import BaseModel

class Supplier(BaseModel):
    """Supplier model for managing medical suppliers/vendors"""
    __tablename__ = 'suppliers'
    
    facility_slug = db.Column(db.String(100), db.ForeignKey('facilities.slug'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        """Convert to dictionary"""
        data = super().to_dict()
        return data