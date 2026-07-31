from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel


class Appointment(BaseModel):
    """Appointment model for scheduling"""
    __tablename__ = 'appointments'
    __table_args__ = (
        Index('idx_appointments_facility_dept', 'facility_slug', 'department_id'),
        Index('idx_appointments_facility_branch', 'facility_slug', 'branch_id'),
        Index('idx_appointments_status_facility', 'status', 'facility_slug'),
        Index('idx_appointments_facility_date', 'facility_slug', 'appointment_date'),
        Index('idx_appointments_facility_doctor_date', 'facility_slug', 'doctor_id', 'appointment_date'),
        Index(
            'uq_appointments_facility_idempotency',
            'facility_slug',
            'idempotency_key',
            unique=True,
        ),
    )

    patient_id = Column(String(36), ForeignKey('patients.id'), nullable=False, index=True)
    doctor_id = Column(String(36), ForeignKey('users.id'), nullable=False, index=True)
    facility_id = Column(String(36), ForeignKey('facilities.id'), nullable=True, index=True)
    facility_slug = Column(String(100), ForeignKey('facilities.slug'), nullable=True, index=True)
    department_id = Column(String(36), nullable=True, index=True)  # legacy clinic/department scope
    branch_id = Column(String(36), ForeignKey('branches.id'), nullable=True, index=True)
    appointment_date = Column(DateTime, nullable=False, index=True)
    scheduled_time = Column(DateTime, nullable=True, index=True)
    duration_minutes = Column(Integer, default=30)
    status = Column(String(50), default='SCHEDULED', index=True)
    reason = Column(Text)
    notes = Column(Text)
    idempotency_key = Column(String(200), nullable=True)
    idempotency_payload_hash = Column(String(64), nullable=True)

    STATUSES = ['SCHEDULED', 'COMPLETED', 'CANCELLED', 'NO_SHOW']

    def to_dict(self):
        """Convert to dictionary with formatted dates"""
        data = super().to_dict()
        if isinstance(self.appointment_date, datetime):
            data['appointment_date'] = self.appointment_date.isoformat()
        return data
