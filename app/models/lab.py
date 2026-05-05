from app.extensions import db
from app.models.base_model import BaseModel

class LabTest(BaseModel):
    """Lab test definitions"""
    __tablename__ = 'lab_tests'
    
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))  # e.g., Blood, Urine, Radiology
    unit = db.Column(db.String(50))  # Unit of measurement
    reference_range = db.Column(db.String(100))  # Normal reference range
    price = db.Column(db.Numeric(10, 2), default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    orders = db.relationship('LabOrder', backref='test', lazy=True)
    
    def to_dict(self):
        data = super().to_dict()
        if self.price:
            data['price'] = float(self.price)
        return data


class LabOrder(BaseModel):
    """Lab orders for patients"""
    __tablename__ = 'lab_orders'
    
    patient_id = db.Column(db.String(36), db.ForeignKey('patients.id'), nullable=False, index=True)
    test_id = db.Column(db.String(36), db.ForeignKey('lab_tests.id'), nullable=False)
    facility_slug = db.Column(db.String(100), db.ForeignKey('facilities.slug'), nullable=True, index=True)
    ordered_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    performed_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    status = db.Column(db.String(50), default='PENDING')  # PENDING, COLLECTED, IN_PROGRESS, COMPLETED, CANCELLED
    priority = db.Column(db.String(20), default='ROUTINE')  # ROUTINE, URGENT, EMERGENCY
    notes = db.Column(db.Text)
    order_date = db.Column(db.DateTime, nullable=False)
    collection_date = db.Column(db.DateTime)
    completed_date = db.Column(db.DateTime)
    
    # Relationships
    results = db.relationship('LabResult', backref='order', lazy=True, cascade='all, delete-orphan')
    
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
    
    order_id = db.Column(db.String(36), db.ForeignKey('lab_orders.id'), nullable=False)
    value = db.Column(db.String(100))
    is_abnormal = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    result_date = db.Column(db.DateTime)
    
    def to_dict(self):
        data = super().to_dict()
        if self.result_date:
            data['result_date'] = self.result_date.isoformat()
        return data
