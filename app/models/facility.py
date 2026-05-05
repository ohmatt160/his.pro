from app.extensions import db
from app.models.base_model import BaseModel

class Facility(BaseModel):
    """Facility model for managing healthcare facilities"""
    __tablename__ = 'facilities'
    
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # hospital/clinic/lab/pharmacy
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    country = db.Column(db.String(100))
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    modules = db.Column(db.JSON, default=list)  # list of enabled modules
    settings = db.Column(db.JSON, default=dict)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    users = db.relationship('User', backref='facility', lazy=True, foreign_keys='User.facility_slug')
    patients = db.relationship('Patient', backref='facility', lazy=True, foreign_keys='Patient.facility_slug')
    appointments = db.relationship('Appointment', backref='facility', lazy=True, foreign_keys='Appointment.facility_slug')
    bills = db.relationship('Invoice', backref='facility', lazy=True, foreign_keys='Invoice.facility_slug')
    lab_orders = db.relationship('LabOrder', backref='facility', lazy=True, foreign_keys='LabOrder.facility_slug')
    pharmacy_orders = db.relationship('Prescription', backref='facility', lazy=True, foreign_keys='Prescription.facility_slug')
    medical_records = db.relationship('MedicalRecord', backref='facility', lazy=True, foreign_keys='MedicalRecord.facility_slug')
    radiology_orders = db.relationship('Radiology', backref='facility', lazy=True, foreign_keys='Radiology.facility_slug')
    inventory_items = db.relationship('Inventory', backref='facility', lazy=True, foreign_keys='Inventory.facility_slug')
    suppliers = db.relationship('Supplier', backref='facility', lazy=True, foreign_keys='Supplier.facility_slug')
    patient_queues = db.relationship('PatientQueue', backref='facility', lazy=True, foreign_keys='PatientQueue.facility_slug')
    alerts = db.relationship('Alert', backref='facility', lazy=True, foreign_keys='Alert.facility_slug')
    
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