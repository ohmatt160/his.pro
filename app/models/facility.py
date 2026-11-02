import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Boolean, JSON, event
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel
from app.utils.tenant_urls import generate_canonical_subdomain


class Facility(BaseModel):
    """Facility model for managing healthcare facilities"""
    __tablename__ = 'facilities'

    name = Column(String(200), nullable=False)
    type = Column(String(50), nullable=False)  # hospital/clinic/lab/pharmacy
    slug = Column(String(100), unique=True, nullable=False, index=True)
    canonical_subdomain = Column(String(63), unique=True, nullable=False, index=True)
    country = Column(String(100))
    address = Column(Text)
    phone = Column(String(20))
    email = Column(String(120))
    hospital_type = Column(String(20), default="single")  # single/multi_clinic
    departments = Column(JSON, default=list)
    modules = Column(JSON, default=list)  # list of enabled modules
    settings = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    deletion_status = Column(
        String(24), nullable=False, default="ACTIVE", server_default="ACTIVE", index=True
    )
    deletion_requested_at = Column(DateTime, nullable=True)
    deletion_scheduled_for = Column(DateTime, nullable=True, index=True)
    deletion_cancelled_at = Column(DateTime, nullable=True)
    deletion_requested_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    deletion_recovery_token_hash = Column(String(64), nullable=True)

    # Relationships
    branches = relationship('Branch', back_populates='facility', lazy=True, foreign_keys='Branch.facility_slug')
    users = relationship('User', backref='facility', lazy=True, foreign_keys='User.facility_slug')
    patients = relationship('Patient', backref='facility', lazy=True, foreign_keys='Patient.facility_slug')
    appointments = relationship('Appointment', backref='facility', lazy=True, foreign_keys='Appointment.facility_slug')
    bills = relationship('Invoice', backref='facility', lazy=True, foreign_keys='Invoice.facility_slug')
    lab_orders = relationship('LabOrder', backref='facility', lazy=True, foreign_keys='LabOrder.facility_slug')
    pharmacy_orders = relationship('Prescription', backref='facility', lazy=True, foreign_keys='Prescription.facility_slug')
    medical_records = relationship('MedicalRecord', backref='facility', lazy=True, foreign_keys='MedicalRecord.facility_slug')
    radiology_orders = relationship('Radiology', backref='facility', lazy=True, foreign_keys='Radiology.facility_slug')
    inventory_items = relationship('Inventory', backref='facility', lazy=True, foreign_keys='Inventory.facility_slug')
    suppliers = relationship('Supplier', backref='facility', lazy=True, foreign_keys='Supplier.facility_slug')
    patient_queues = relationship('PatientQueue', backref='facility', lazy=True, foreign_keys='PatientQueue.facility_slug')
    alerts = relationship('Alert', backref='facility', lazy=True, foreign_keys='Alert.facility_slug')

    # Facility types
    FACILITY_TYPES = ['hospital', 'clinic', 'lab', 'pharmacy']
    DELETION_STATUSES = ("ACTIVE", "PENDING_DELETION", "PURGED")

    # Available modules
    AVAILABLE_MODULES = [
        'reception',
        'records',
        'consultations',
        'nursing',
        'lab',
        'pharmacy',
        'billing',
        'radiology',
        'inventory',
        'reports',
    ]

    MODULE_ALIASES = {
        'appointments': 'reception',
        'patients': 'reception',
        'medical_records': 'records',
        'dashboard': 'reports',
    }

    def to_dict(self):
        """Convert to dictionary"""
        data = super().to_dict()
        return data


@event.listens_for(Facility, "before_insert")
def _assign_canonical_subdomain(_mapper, _connection, facility: Facility) -> None:
    if not facility.id:
        facility.id = str(uuid.uuid4())
    if not facility.canonical_subdomain:
        facility.canonical_subdomain = generate_canonical_subdomain(
            facility.slug,
            facility.id,
        )
