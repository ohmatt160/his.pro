from datetime import datetime
from app.extensions import db
from app.models.base_model import BaseModel

class PatientQueue(BaseModel):
    """PatientQueue model for managing patient visit队列"""
    __tablename__ = 'patient_queues'
    
    facility_slug = db.Column(db.String(100), db.ForeignKey('facilities.slug'), nullable=False, index=True)
    patient_id = db.Column(db.String(36), db.ForeignKey('patients.id'), nullable=False, index=True)
    appointment_id = db.Column(db.String(36), db.ForeignKey('appointments.id'), nullable=True)
    department = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), default='waiting', index=True)  # waiting/in_progress/completed/no_show
    queue_number = db.Column(db.Integer, nullable=False)
    priority = db.Column(db.String(20), default='normal')  # normal/urgent
    checked_in_at = db.Column(db.DateTime, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    patient = db.relationship('Patient', backref='queue_entries', lazy=True)
    appointment = db.relationship('Appointment', backref='queue_entries', lazy=True)
    
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