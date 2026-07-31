from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, text
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel


class PatientQueue(BaseModel):
    """PatientQueue model for managing patient visit队列"""
    __tablename__ = 'patient_queues'
    __table_args__ = (
        Index('idx_patient_queues_facility_branch_status', 'facility_slug', 'branch_id', 'status'),
        Index('idx_patient_queues_facility_created', 'facility_slug', 'created_at'),
        Index('idx_patient_queues_facility_patient', 'facility_slug', 'patient_id'),
        Index(
            'uq_patient_queues_active_patient',
            'facility_slug',
            'patient_id',
            unique=True,
            postgresql_where=text("status IN ('waiting', 'in_progress')"),
            sqlite_where=text("status IN ('waiting', 'in_progress')"),
        ),
        Index(
            'uq_patient_queues_facility_idempotency',
            'facility_slug',
            'idempotency_key',
            unique=True,
        ),
    )

    facility_id = Column(String(36), ForeignKey('facilities.id'), nullable=True, index=True)
    facility_slug = Column(String(100), ForeignKey('facilities.slug'), nullable=False, index=True)
    patient_id = Column(String(36), ForeignKey('patients.id'), nullable=False, index=True)
    appointment_id = Column(String(36), ForeignKey('appointments.id'), nullable=True)
    branch_id = Column(String(36), ForeignKey('branches.id'), nullable=True, index=True)
    department = Column(String(100), nullable=False)
    status = Column(String(50), default='waiting', index=True)  # waiting/in_progress/completed/no_show
    queue_number = Column(Integer, nullable=False)
    priority = Column(String(20), default='normal')  # normal/urgent
    idempotency_key = Column(String(200), nullable=True)
    idempotency_payload_hash = Column(String(64), nullable=True)
    checked_in_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    patient = relationship('Patient', backref='queue_entries', lazy=True)
    appointment = relationship('Appointment', backref='queue_entries', lazy=True)

    # Statuses
    STATUSES = ['waiting', 'in_progress', 'completed', 'no_show']

    # Priorities
    PRIORITIES = ['normal', 'urgent']

    def to_dict(self):
        """Convert to dictionary"""
        data = super().to_dict()
        return data

    def check_in(self):
        """Mark patient as checked in"""
        self.checked_in_at = datetime.utcnow()
        self.status = 'waiting'
        return self

    def start_visit(self):
        """Mark visit as started"""
        self.started_at = datetime.utcnow()
        self.status = 'in_progress'
        return self

    def complete_visit(self):
        """Mark visit as completed"""
        self.completed_at = datetime.utcnow()
        self.status = 'completed'
        return self

    def mark_no_show(self):
        """Mark patient as no show"""
        self.completed_at = datetime.utcnow()
        self.status = 'no_show'
        return self
