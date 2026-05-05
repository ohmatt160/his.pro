from app.extensions import db
from app.models.base_model import BaseModel

class Medication(BaseModel):
    """Medication inventory"""
    __tablename__ = 'medications'
    
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    generic_name = db.Column(db.String(200))
    description = db.Column(db.Text)
    category = db.Column(db.String(100))  # e.g., Antibiotic, Pain Relief
    unit = db.Column(db.String(50))  # e.g., tablet, ml, vial
    strength = db.Column(db.String(50))  # e.g., 500mg
    price = db.Column(db.Numeric(10, 2), default=0)
    reorder_level = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=True)
    facility_slug = db.Column(db.String(100), db.ForeignKey('facilities.slug'), nullable=True, index=True)
    
    # Relationships
    inventory = db.relationship('PharmacyInventory', backref='medication', uselist=False)
    prescription_items = db.relationship('PrescriptionItem', backref='medication', lazy=True)
    
    def to_dict(self):
        data = super().to_dict()
        if self.price:
            data['price'] = float(self.price)
        return data


class PharmacyInventory(BaseModel):
    """Pharmacy inventory tracking"""
    __tablename__ = 'pharmacy_inventory'
    
    medication_id = db.Column(db.String(36), db.ForeignKey('medications.id'), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    expiry_date = db.Column(db.Date)
    batch_number = db.Column(db.String(100))
    location = db.Column(db.String(50))  # Storage location
    
    def to_dict(self):
        data = super().to_dict()
        if self.expiry_date:
            data['expiry_date'] = self.expiry_date.isoformat()
        return data


class Prescription(BaseModel):
    """Prescriptions for patients"""
    __tablename__ = 'prescriptions'
    
    patient_id = db.Column(db.String(36), db.ForeignKey('patients.id'), nullable=False, index=True)
    prescribed_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    facility_slug = db.Column(db.String(100), db.ForeignKey('facilities.slug'), nullable=True, index=True)
    status = db.Column(db.String(50), default='PENDING')  # PENDING, DISPENSED, CANCELLED
    notes = db.Column(db.Text)
    prescription_date = db.Column(db.DateTime, nullable=False)
    dispensed_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    dispensed_date = db.Column(db.DateTime)
    
    # Relationships
    items = db.relationship('PrescriptionItem', backref='prescription', lazy=True, cascade='all, delete-orphan')
    
    STATUSES = ['PENDING', 'DISPENSED', 'CANCELLED']
    
    def to_dict(self):
        data = super().to_dict()
        if self.prescription_date:
            data['prescription_date'] = self.prescription_date.isoformat()
        if self.dispensed_date:
            data['dispensed_date'] = self.dispensed_date.isoformat()
        return data


class PrescriptionItem(BaseModel):
    """Individual items in a prescription"""
    __tablename__ = 'prescription_items'
    
    prescription_id = db.Column(db.String(36), db.ForeignKey('prescriptions.id'), nullable=False)
    medication_id = db.Column(db.String(36), db.ForeignKey('medications.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    dosage = db.Column(db.String(100))  # e.g., 1 tablet thrice daily
    instructions = db.Column(db.Text)
    is_dispensed = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return super().to_dict()
