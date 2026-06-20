from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel


class User(BaseModel):
    """User model with role-based access control"""
    __tablename__ = 'users'

    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(20))
    department = Column(String(100))
    department_id = Column(String(36), nullable=True, index=True)  # legacy branch/location assignment
    departments = Column(JSON, default=list)  # legacy multi-branch access list
    branch_id = Column(String(36), ForeignKey('branches.id'), nullable=True, index=True)
    branch_ids = Column(JSON, default=list)
    facility_id = Column(String(36), ForeignKey('facilities.id'), nullable=True, index=True)
    facility_slug = Column(String(100), ForeignKey('facilities.slug'), nullable=True, index=True)
    must_change_password = Column(Boolean, default=False)
    last_password_change = Column(DateTime, nullable=True)
    last_active = Column(DateTime, nullable=True)

    # Relationships
    patients = relationship('Patient', backref='created_by_user', lazy=True, foreign_keys='Patient.created_by')
    appointments_as_doctor = relationship('Appointment', backref='doctor', lazy=True, foreign_keys='Appointment.doctor_id')

    def set_password(self, password):
        """Hash and set password using werkzeug"""
        self.password_hash = generate_password_hash(
            password,
            method='pbkdf2:sha256',
            salt_length=16,
        )

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
        return ['ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE', 'LAB_TECH', 'PHARMACIST', 'RECEPTIONIST']
