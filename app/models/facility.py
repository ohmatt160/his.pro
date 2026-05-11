from sqlalchemy import Column, String, Text, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel


class Facility(BaseModel):
    """Facility model for managing healthcare facilities"""
    __tablename__ = 'facilities'

    name = Column(String(200), nullable=False)
    type = Column(String(50), nullable=False)  # hospital/clinic/lab/pharmacy
    slug = Column(String(100), unique=True, nullable=False, index=True)
    country = Column(String(100))
    address = Column(Text)
    phone = Column(String(20))
    email = Column(String(120))
    modules = Column(JSON, default=list)  # list of enabled modules
    settings = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)

    # Relationships
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

    # Available modules
    AVAILABLE_MODULES = [
        'appointments',
        'patients',
        'billing',
        'lab',
        'pharmacy',
        'radiology',
        'inventory',
        'medical_records',
        'reports',
        'dashboard'
    ]

    def to_dict(self):
        """Convert to dictionary"""
        data = super().to_dict()
        return data
