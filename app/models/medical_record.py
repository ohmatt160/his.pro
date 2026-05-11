from sqlalchemy import Column, String, JSON, Text, DateTime, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel


class MedicalRecord(BaseModel):
    """Electronic Medical Records for patients"""
    __tablename__ = 'medical_records'

    patient_id = Column(String(36), ForeignKey('patients.id'), nullable=False, index=True)
    appointment_id = Column(String(36), ForeignKey('appointments.id'))
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

    # Relationships
    patient = relationship('Patient', backref='medical_records')

    def to_dict(self):
        data = super().to_dict()
        return data


class ClinicalNote(BaseModel):
    """Clinical notes for patient visits"""
    __tablename__ = 'clinical_notes'

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
