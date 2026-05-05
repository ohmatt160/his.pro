from datetime import datetime
from app.extensions import db
from app.models.base_model import BaseModel

class Appointment(BaseModel):
    """Appointment model for scheduling"""
    __tablename__ = 'appointments'
    
    patient_id = db.Column(db.String(36), db.ForeignKey('patients.id'), nullable=False, index=True)
    doctor_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    facility_slug = db.Column(db.String(100), db.ForeignKey('facilities.slug'), nullable=True, index=True)
    appointment_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), default='SCHEDULED')
    reason = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    STATUSES = ['SCHEDULED', 'COMPLETED', 'CANCELLED', 'NO_SHOW']
    
    def to_dict(self):
        """Convert to dictionary with formatted dates"""
        data = super().to_dict()
        if isinstance(self.appointment_date, datetime):
            data['appointment_date'] = self.appointment_date.isoformat()
        return data
