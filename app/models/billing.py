from app.extensions import db
from app.models.base_model import BaseModel

class Invoice(BaseModel):
    """Invoice for patient services"""
    __tablename__ = 'invoices'
    
    patient_id = db.Column(db.String(36), db.ForeignKey('patients.id'), nullable=False, index=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    facility_slug = db.Column(db.String(100), db.ForeignKey('facilities.slug'), nullable=True, index=True)
    status = db.Column(db.String(50), default='PENDING')  # PENDING, PAID, PARTIAL, CANCELLED
    subtotal = db.Column(db.Numeric(10, 2), default=0)
    tax = db.Column(db.Numeric(10, 2), default=0)
    discount = db.Column(db.Numeric(10, 2), default=0)
    total = db.Column(db.Numeric(10, 2), default=0)
    notes = db.Column(db.Text)
    due_date = db.Column(db.Date)
    invoice_date = db.Column(db.DateTime, nullable=False)
    paid_date = db.Column(db.DateTime)
    
    # Relationships
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='invoice', lazy=True, cascade='all, delete-orphan')
    
    STATUSES = ['PENDING', 'PAID', 'PARTIAL', 'CANCELLED']
    
    def calculate_total(self):
        """Calculate total from items"""
        self.subtotal = sum(item.total for item in self.items)
        self.total = self.subtotal + self.tax - self.discount
        return self.total
    
    def to_dict(self):
        data = super().to_dict()
        if self.subtotal:
            data['subtotal'] = float(self.subtotal)
        if self.tax:
            data['tax'] = float(self.tax)
        if self.discount:
            data['discount'] = float(self.discount)
        if self.total:
            data['total'] = float(self.total)
        if self.invoice_date:
            data['invoice_date'] = self.invoice_date.isoformat()
        if self.paid_date:
            data['paid_date'] = self.paid_date.isoformat()
        if self.due_date:
            data['due_date'] = self.due_date.isoformat()
        return data


class InvoiceItem(BaseModel):
    """Individual items in an invoice"""
    __tablename__ = 'invoice_items'
    
    invoice_id = db.Column(db.String(36), db.ForeignKey('invoices.id'), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Numeric(10, 2), default=0)
    total = db.Column(db.Numeric(10, 2), default=0)
    
    def calculate_total(self):
        self.total = self.quantity * self.unit_price
        return self.total
    
    def to_dict(self):
        data = super().to_dict()
        if self.unit_price:
            data['unit_price'] = float(self.unit_price)
        if self.total:
            data['total'] = float(self.total)
        return data


class Payment(BaseModel):
    """Payment records"""
    __tablename__ = 'payments'
    
    invoice_id = db.Column(db.String(36), db.ForeignKey('invoices.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(50))  # CASH, CARD, TRANSFER, INSURANCE
    reference_number = db.Column(db.String(100))
    notes = db.Column(db.Text)
    payment_date = db.Column(db.DateTime, nullable=False)
    
    PAYMENT_METHODS = ['CASH', 'CARD', 'TRANSFER', 'INSURANCE']
    
    def to_dict(self):
        data = super().to_dict()
        if self.amount:
            data['amount'] = float(self.amount)
        if self.payment_date:
            data['payment_date'] = self.payment_date.isoformat()
        return data


class InsuranceProvider(BaseModel):
    """Insurance providers"""
    __tablename__ = 'insurance_providers'
    
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    contact_number = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return super().to_dict()


class InsuranceClaim(BaseModel):
    """Insurance claims"""
    __tablename__ = 'insurance_claims'
    
    invoice_id = db.Column(db.String(36), db.ForeignKey('invoices.id'), nullable=False)
    insurance_provider_id = db.Column(db.String(36), db.ForeignKey('insurance_providers.id'))
    policy_number = db.Column(db.String(100))
    claim_number = db.Column(db.String(50), unique=True)
    claimed_amount = db.Column(db.Numeric(10, 2), default=0)
    approved_amount = db.Column(db.Numeric(10, 2), default=0)
    status = db.Column(db.String(50), default='PENDING')  # PENDING, SUBMITTED, APPROVED, REJECTED
    claim_date = db.Column(db.DateTime)
    settlement_date = db.Column(db.DateTime)
    
    STATUSES = ['PENDING', 'SUBMITTED', 'APPROVED', 'REJECTED']
    
    def to_dict(self):
        data = super().to_dict()
        if self.claimed_amount:
            data['claimed_amount'] = float(self.claimed_amount)
        if self.approved_amount:
            data['approved_amount'] = float(self.approved_amount)
        if self.claim_date:
            data['claim_date'] = self.claim_date.isoformat()
        if self.settlement_date:
            data['settlement_date'] = self.settlement_date.isoformat()
        return data
