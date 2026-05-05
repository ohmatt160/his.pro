from datetime import datetime
from app.extensions import db
from app.models.base_model import BaseModel

class Radiology(BaseModel):
    """Radiology model for managing imaging orders and results"""
    __tablename__ = 'radiology_orders'
    
    patient_id = db.Column(db.String(36), db.ForeignKey('patients.id'), nullable=False, index=True)
    facility_slug = db.Column(db.String(100), db.ForeignKey('facilities.slug'), nullable=False, index=True)
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    modality = db.Column(db.String(50), nullable=False)  # X-ray/CT/MRI/Ultrasound
    body_part = db.Column(db.String(100), nullable=False)
    clinical_notes = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending', index=True)  # pending/ordered/completed/cancelled
    requested_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    radiologist_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    report = db.Column(db.Text)
    report_date = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    patient = db.relationship('Patient', backref='radiology_orders', lazy=True)
    requester = db.relationship('User', foreign_keys=[requested_by], backref='radiology_requests', lazy=True)
    radiologist = db.relationship('User', foreign_keys=[radiologist_id], backref='radiology_reports', lazy=True)
    
    # Modalities
    MODALITIES = ['X-ray', 'CT', 'MRI', 'Ultrasound']
    
    # Statuses
    STATUSES = ['pending', 'ordered', 'completed', 'cancelled']
    
    def to_dict(self):
        """Convert to dictionary"""
        data = super().to_dict()
        return data