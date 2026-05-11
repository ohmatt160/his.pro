from sqlalchemy import Column, String, Date, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel


class Patient(BaseModel):
    """Patient model for storing medical records"""
    __tablename__ = 'patients'

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(20))
    phone = Column(String(20))
    email = Column(String(120))
    address = Column(Text)
    blood_type = Column(String(5))
    medical_history = Column(JSON, default=dict)
    emergency_contact_name = Column(String(100))
    emergency_contact_phone = Column(String(20))
    created_by = Column(String(36), ForeignKey('users.id'), index=True)
    facility_slug = Column(String(100), ForeignKey('facilities.slug'), nullable=True, index=True)

    # Relationships
    appointments = relationship('Appointment', backref='patient', lazy=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def to_dict(self):
        """Convert to dictionary with computed fields"""
        data = super().to_dict()
        data['full_name'] = self.full_name
        return data
