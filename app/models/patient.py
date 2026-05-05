from app.extensions import db
from app.models.base_model import BaseModel

class Patient(BaseModel):
    """Patient model for storing medical records"""
    __tablename__ = 'patients'
    
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(20))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    blood_type = db.Column(db.String(5))
    medical_history = db.Column(db.JSON, default=dict)
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_phone = db.Column(db.String(20))
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'), index=True)
    facility_slug = db.Column(db.String(100), db.ForeignKey('facilities.slug'), nullable=True, index=True)
    
    # Relationships
    appointments = db.relationship('Appointment', backref='patient', lazy=True)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def to_dict(self):
        """Convert to dictionary with computed fields"""
        data = super().to_dict()
        data['full_name'] = self.full_name
        return data
