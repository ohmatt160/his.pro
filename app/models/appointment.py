from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel


class Appointment(BaseModel):
    """Appointment model for scheduling"""
    __tablename__ = 'appointments'

    patient_id = Column(String(36), ForeignKey('patients.id'), nullable=False, index=True)
    doctor_id = Column(String(36), ForeignKey('users.id'), nullable=False, index=True)
    facility_slug = Column(String(100), ForeignKey('facilities.slug'), nullable=True, index=True)
    appointment_date = Column(DateTime, nullable=False)
    status = Column(String(50), default='SCHEDULED')
    reason = Column(Text)
    notes = Column(Text)

    STATUSES = ['SCHEDULED', 'COMPLETED', 'CANCELLED', 'NO_SHOW']

    def to_dict(self):
        """Convert to dictionary with formatted dates"""
        data = super().to_dict()
        if isinstance(self.appointment_date, datetime):
            data['appointment_date'] = self.appointment_date.isoformat()
        return data
