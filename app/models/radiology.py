from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel


class Radiology(BaseModel):
    """Radiology model for managing imaging orders and results"""
    __tablename__ = 'radiology_orders'

    patient_id = Column(String(36), ForeignKey('patients.id'), nullable=False, index=True)
    facility_slug = Column(String(100), ForeignKey('facilities.slug'), nullable=False, index=True)
    request_date = Column(DateTime, default=datetime.utcnow)
    modality = Column(String(50), nullable=False)  # X-ray/CT/MRI/Ultrasound
    body_part = Column(String(100), nullable=False)
    clinical_notes = Column(Text)
    status = Column(String(50), default='pending', index=True)  # pending/ordered/completed/cancelled
    requested_by = Column(String(36), ForeignKey('users.id'), nullable=False)
    radiologist_id = Column(String(36), ForeignKey('users.id'), nullable=True)
    report = Column(Text)
    report_date = Column(DateTime, nullable=True)

    # Relationships
    patient = relationship('Patient', backref='radiology_orders', lazy=True)
    requester = relationship('User', foreign_keys=[requested_by], backref='radiology_requests', lazy=True)
    radiologist = relationship('User', foreign_keys=[radiologist_id], backref='radiology_reports', lazy=True)

    # Modalities
    MODALITIES = ['X-ray', 'CT', 'MRI', 'Ultrasound']

    # Statuses
    STATUSES = ['pending', 'ordered', 'completed', 'cancelled']

    def to_dict(self):
        """Convert to dictionary"""
        data = super().to_dict()
        return data
