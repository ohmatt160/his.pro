from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.models.base_model import BaseModel

class User(BaseModel):
    """User model with role-based access control"""
    __tablename__ = 'users'
    
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    department = db.Column(db.String(100))
    facility_slug = db.Column(db.String(100), db.ForeignKey('facilities.slug'), nullable=True, index=True)
    must_change_password = db.Column(db.Boolean, default=False)
    last_password_change = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    patients = db.relationship('Patient', backref='created_by_user', lazy=True, foreign_keys='Patient.created_by')
    appointments_as_doctor = db.relationship('Appointment', backref='doctor', lazy=True, foreign_keys='Appointment.doctor_id')
    
    def set_password(self, password):
        """Hash and set password using werkzeug"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert to dictionary without sensitive data"""
        data = super().to_dict()
        data.pop('password_hash', None)
        return data
    
    @staticmethod
    def get_roles():
        return ['ADMIN', 'DOCTOR', 'NURSE', 'LAB_TECH', 'PHARMACIST', 'RECEPTIONIST']
