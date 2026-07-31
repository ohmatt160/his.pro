from sqlalchemy import Column, String, Numeric, Integer, Boolean, Date, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel


class Medication(BaseModel):
    """Medication inventory"""
    __tablename__ = 'medications'
    __table_args__ = (
        Index('idx_medications_facility_active', 'facility_slug', 'is_active'),
        Index('uq_medications_facility_code', 'facility_slug', 'code', unique=True),
    )

    name = Column(String(200), nullable=False)
    code = Column(String(50), nullable=False)
    generic_name = Column(String(200))
    description = Column(Text)
    category = Column(String(100))  # e.g., Antibiotic, Pain Relief
    unit = Column(String(50))  # e.g., tablet, ml, vial
    strength = Column(String(50))  # e.g., 500mg
    price = Column(Numeric(10, 2), default=0)
    reorder_level = Column(Integer, default=10)
    is_active = Column(Boolean, default=True)
    facility_id = Column(String(36), ForeignKey('facilities.id'), nullable=True, index=True)
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
    __table_args__ = (
        Index(
            'uq_pharmacy_inventory_medication',
            'medication_id',
            unique=True,
        ),
    )

    medication_id = Column(String(36), ForeignKey('medications.id'), nullable=False, index=True)
    quantity = Column(Integer, default=0)
    expiry_date = Column(Date, index=True)
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
    __table_args__ = (
        Index('idx_prescriptions_facility_dept', 'facility_slug', 'department_id'),
        Index('idx_prescriptions_facility_branch', 'facility_slug', 'branch_id'),
        Index('idx_prescriptions_status_facility', 'status', 'facility_slug'),
        Index('idx_prescriptions_facility_date', 'facility_slug', 'prescription_date'),
        Index('idx_prescriptions_facility_patient', 'facility_slug', 'patient_id'),
        Index(
            'uq_prescriptions_facility_idempotency',
            'facility_slug',
            'idempotency_key',
            unique=True,
        ),
    )

    patient_id = Column(String(36), ForeignKey('patients.id'), nullable=False, index=True)
    prescribed_by = Column(String(36), ForeignKey('users.id'), index=True)
    facility_id = Column(String(36), ForeignKey('facilities.id'), nullable=True, index=True)
    facility_slug = Column(String(100), ForeignKey('facilities.slug'), nullable=True, index=True)
    department_id = Column(String(36), nullable=True, index=True)  # legacy clinic/department scope
    branch_id = Column(String(36), ForeignKey('branches.id'), nullable=True, index=True)
    status = Column(String(50), default='PENDING', index=True)  # PENDING, DISPENSED, CANCELLED
    notes = Column(Text)
    idempotency_key = Column(String(200), nullable=True)
    idempotency_payload_hash = Column(String(64), nullable=True)
    prescription_date = Column(DateTime, nullable=False, index=True)
    dispensed_by = Column(String(36), ForeignKey('users.id'), index=True)
    dispensed_date = Column(DateTime, index=True)

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
