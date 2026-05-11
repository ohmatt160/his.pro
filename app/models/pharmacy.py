from sqlalchemy import Column, String, Numeric, Integer, Boolean, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel


class Medication(BaseModel):
    """Medication inventory"""
    __tablename__ = 'medications'

    name = Column(String(200), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    generic_name = Column(String(200))
    description = Column(Text)
    category = Column(String(100))  # e.g., Antibiotic, Pain Relief
    unit = Column(String(50))  # e.g., tablet, ml, vial
    strength = Column(String(50))  # e.g., 500mg
    price = Column(Numeric(10, 2), default=0)
    reorder_level = Column(Integer, default=10)
    is_active = Column(Boolean, default=True)
    facility_slug = Column(String(100), ForeignKey('facilities.slug'), nullable=True, index=True)

    # Relationships
    inventory = relationship('PharmacyInventory', backref='medication', uselist=False)
    prescription_items = relationship('PrescriptionItem', backref='medication', lazy=True)

    def to_dict(self):
        data = super().to_dict()
        if self.price:
            data['price'] = float(self.price)
        return data


class PharmacyInventory(BaseModel):
    """Pharmacy inventory tracking"""
    __tablename__ = 'pharmacy_inventory'

    medication_id = Column(String(36), ForeignKey('medications.id'), nullable=False)
    quantity = Column(Integer, default=0)
    expiry_date = Column(Date)
    batch_number = Column(String(100))
    location = Column(String(50))  # Storage location

    def to_dict(self):
        data = super().to_dict()
        if self.expiry_date:
            data['expiry_date'] = self.expiry_date.isoformat()
        return data


class Prescription(BaseModel):
    """Prescriptions for patients"""
    __tablename__ = 'prescriptions'

    patient_id = Column(String(36), ForeignKey('patients.id'), nullable=False, index=True)
    prescribed_by = Column(String(36), ForeignKey('users.id'))
    facility_slug = Column(String(100), ForeignKey('facilities.slug'), nullable=True, index=True)
    status = Column(String(50), default='PENDING')  # PENDING, DISPENSED, CANCELLED
    notes = Column(Text)
    prescription_date = Column(DateTime, nullable=False)
    dispensed_by = Column(String(36), ForeignKey('users.id'))
    dispensed_date = Column(DateTime)

    # Relationships
    items = relationship('PrescriptionItem', backref='prescription', lazy=True, cascade='all, delete-orphan')

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

    prescription_id = Column(String(36), ForeignKey('prescriptions.id'), nullable=False)
    medication_id = Column(String(36), ForeignKey('medications.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    dosage = Column(String(100))  # e.g., 1 tablet thrice daily
    instructions = Column(Text)
    is_dispensed = Column(Boolean, default=False)

    def to_dict(self):
        return super().to_dict()
