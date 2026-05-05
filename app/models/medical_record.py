from app.extensions import db
from app.models.base_model import BaseModel

class MedicalRecord(BaseModel):
    """Electronic Medical Records for patients"""
    __tablename__ = 'medical_records'
    
    patient_id = db.Column(db.String(36), db.ForeignKey('patients.id'), nullable=False, index=True)
    appointment_id = db.Column(db.String(36), db.ForeignKey('appointments.id'))
    facility_slug = db.Column(db.String(100), db.ForeignKey('facilities.slug'), nullable=True, index=True)
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    
    # Clinical data
    chief_complaint = db.Column(db.Text)
    vital_signs = db.Column(db.JSON, default=dict)  # BP, temp, pulse, etc.
    symptoms = db.Column(db.JSON, default=list)
    diagnosis = db.Column(db.JSON, default=list)  # Multiple diagnoses
    treatment_plan = db.Column(db.Text)
    prescriptions = db.Column(db.JSON, default=list)  # Medications prescribed
    lab_orders = db.Column(db.JSON, default=list)  # Lab tests ordered
    follow_up_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    
    # Relationships
    patient = db.relationship('Patient', backref='medical_records')
    
    def to_dict(self):
        data = super().to_dict()
        return data


class ClinicalNote(BaseModel):
    """Clinical notes for patient visits"""
    __tablename__ = 'clinical_notes'
    
    patient_id = db.Column(db.String(36), db.ForeignKey('patients.id'), nullable=False)
    record_id = db.Column(db.String(36), db.ForeignKey('medical_records.id'))
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    
    note_type = db.Column(db.String(50))  # PROGRESS, INITIAL, DISCHARGE, REFERRAL
    title = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    is_confidential = db.Column(db.Boolean, default=False)
    
    NOTE_TYPES = ['PROGRESS', 'INITIAL', 'DISCHARGE', 'REFERRAL']
    
    def to_dict(self):
        return super().to_dict()
