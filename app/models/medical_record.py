from sqlalchemy import Column, String, JSON, Text, DateTime, Date, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel


class MedicalRecord(BaseModel):
    """Electronic Medical Records for patients"""
    __tablename__ = 'medical_records'
    __table_args__ = (
        Index('idx_medical_records_facility_patient_created', 'facility_slug', 'patient_id', 'created_at'),
        Index('idx_medical_records_facility_appointment', 'facility_slug', 'appointment_id'),
        Index('idx_medical_records_facility_created', 'facility_slug', 'created_at'),
        Index('idx_medical_records_facility_status_created', 'facility_slug', 'status', 'created_at'),
        Index(
            'uq_medical_records_facility_idempotency',
            'facility_slug',
            'idempotency_key',
            unique=True,
        ),
    )

    patient_id = Column(String(36), ForeignKey('patients.id'), nullable=False, index=True)
    appointment_id = Column(String(36), ForeignKey('appointments.id'))
    facility_id = Column(String(36), ForeignKey('facilities.id'), nullable=True, index=True)
    facility_slug = Column(String(100), ForeignKey('facilities.slug'), nullable=True, index=True)
    created_by = Column(String(36), ForeignKey('users.id'))

    # Clinical data
    chief_complaint = Column(Text)
    vital_signs = Column(JSON, default=dict)  # BP, temp, pulse, etc.
    symptoms = Column(JSON, default=list)
    diagnosis = Column(JSON, default=list)  # Multiple diagnoses
    treatment_plan = Column(Text)
    prescriptions = Column(JSON, default=list)  # Medications prescribed
    lab_orders = Column(JSON, default=list)  # Lab tests ordered
    follow_up_date = Column(Date)
    notes = Column(Text)
    idempotency_key = Column(String(200), nullable=True)
    idempotency_payload_hash = Column(String(64), nullable=True)
    status = Column(String(20), nullable=False, default="ACTIVE", index=True)
    void_reason = Column(Text, nullable=True)
    voided_at = Column(DateTime, nullable=True)
    voided_by = Column(String(36), ForeignKey('users.id'), nullable=True)

    # Relationships
    patient = relationship('Patient', backref='medical_records')
    appointment = relationship('Appointment', backref='medical_records')

    def to_dict(self):
        data = super().to_dict()
        return data


class ClinicalNote(BaseModel):
    """Clinical notes for patient visits"""
    __tablename__ = 'clinical_notes'
    __table_args__ = (
        Index('idx_clinical_notes_patient_created', 'patient_id', 'created_at'),
        Index('idx_clinical_notes_record_created', 'record_id', 'created_at'),
    )

    patient_id = Column(String(36), ForeignKey('patients.id'), nullable=False)
    record_id = Column(String(36), ForeignKey('medical_records.id'))
    created_by = Column(String(36), ForeignKey('users.id'))

    note_type = Column(String(50))  # PROGRESS, INITIAL, DISCHARGE, REFERRAL
    title = Column(String(200))
    content = Column(Text, nullable=False)
    is_confidential = Column(Boolean, default=False)

    NOTE_TYPES = ['PROGRESS', 'INITIAL', 'DISCHARGE', 'REFERRAL']

    def to_dict(self):
        return super().to_dict()
