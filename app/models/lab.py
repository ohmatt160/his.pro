from sqlalchemy import Column, String, Numeric, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel


class LabTest(BaseModel):
    """Lab test definitions"""
    __tablename__ = 'lab_tests'

    name = Column(String(200), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    category = Column(String(100))  # e.g., Blood, Urine, Radiology
    unit = Column(String(50))  # Unit of measurement
    reference_range = Column(String(100))  # Normal reference range
    price = Column(Numeric(10, 2), default=0)
    is_active = Column(Boolean, default=True)

    # Relationships
    orders = relationship('LabOrder', backref='test', lazy=True)

    def to_dict(self):
        data = super().to_dict()
        if self.price:
            data['price'] = float(self.price)
        return data


class LabOrder(BaseModel):
    """Lab orders for patients"""
    __tablename__ = 'lab_orders'
    __table_args__ = (
        Index('idx_lab_orders_facility_dept', 'facility_slug', 'department_id'),
        Index('idx_lab_orders_facility_branch', 'facility_slug', 'branch_id'),
        Index('idx_lab_orders_status_facility', 'status', 'facility_slug'),
        Index('idx_lab_orders_facility_date', 'facility_slug', 'order_date'),
        Index('idx_lab_orders_facility_patient', 'facility_slug', 'patient_id'),
    )

    patient_id = Column(String(36), ForeignKey('patients.id'), nullable=False, index=True)
    test_id = Column(String(36), ForeignKey('lab_tests.id'), nullable=False)
    facility_id = Column(String(36), ForeignKey('facilities.id'), nullable=True, index=True)
    facility_slug = Column(String(100), ForeignKey('facilities.slug'), nullable=True, index=True)
    department_id = Column(String(36), nullable=True, index=True)
    branch_id = Column(String(36), ForeignKey('branches.id'), nullable=True, index=True)
    ordered_by = Column(String(36), ForeignKey('users.id'))
    performed_by = Column(String(36), ForeignKey('users.id'))
    status = Column(String(50), default='PENDING', index=True)  # PENDING, COLLECTED, IN_PROGRESS, COMPLETED, CANCELLED
    priority = Column(String(20), default='ROUTINE')  # ROUTINE, URGENT, EMERGENCY
    notes = Column(Text)
    order_date = Column(DateTime, nullable=False, index=True)
    collection_date = Column(DateTime)
    completed_date = Column(DateTime)

    # Relationships
    results = relationship('LabResult', backref='order', lazy=True, cascade='all, delete-orphan')

    STATUSES = ['PENDING', 'COLLECTED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']
    PRIORITIES = ['ROUTINE', 'URGENT', 'EMERGENCY']

    def to_dict(self):
        data = super().to_dict()
        if self.order_date:
            data['order_date'] = self.order_date.isoformat()
        if self.collection_date:
            data['collection_date'] = self.collection_date.isoformat()
        if self.completed_date:
            data['completed_date'] = self.completed_date.isoformat()
        return data


class LabResult(BaseModel):
    """Lab results for orders"""
    __tablename__ = 'lab_results'

    order_id = Column(String(36), ForeignKey('lab_orders.id'), nullable=False, index=True)
    value = Column(String(100))
    is_abnormal = Column(Boolean, default=False)
    notes = Column(Text)
    result_date = Column(DateTime)

    def to_dict(self):
        data = super().to_dict()
        if self.result_date:
            data['result_date'] = self.result_date.isoformat()
        return data
