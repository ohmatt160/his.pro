from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel


class User(BaseModel):
    """User model with role-based access control"""
    __tablename__ = 'users'

    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    department = Column(String(100))
    facility_slug = Column(String(100), ForeignKey('facilities.slug'), nullable=True, index=True)
    must_change_password = Column(Boolean, default=False)
    last_password_change = Column(DateTime, nullable=True)

    # Relationships
    patients = relationship('Patient', backref='created_by_user', lazy=True, foreign_keys='Patient.created_by')
    appointments_as_doctor = relationship('Appointment', backref='doctor', lazy=True, foreign_keys='Appointment.doctor_id')

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
