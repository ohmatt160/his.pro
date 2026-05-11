from sqlalchemy import Column, String, Numeric, Text, Boolean, DateTime, Date, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel


class Invoice(BaseModel):
    """Invoice for patient services"""
    __tablename__ = 'invoices'

    patient_id = Column(String(36), ForeignKey('patients.id'), nullable=False, index=True)
    invoice_number = Column(String(50), unique=True, nullable=False)
    facility_slug = Column(String(100), ForeignKey('facilities.slug'), nullable=True, index=True)
    status = Column(String(50), default='PENDING')  # PENDING, PAID, PARTIAL, CANCELLED
    subtotal = Column(Numeric(10, 2), default=0)
    tax = Column(Numeric(10, 2), default=0)
    discount = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), default=0)
    notes = Column(Text)
    due_date = Column(Date)
    invoice_date = Column(DateTime, nullable=False)
    paid_date = Column(DateTime)

    # Relationships
    items = relationship('InvoiceItem', backref='invoice', lazy=True, cascade='all, delete-orphan')
    payments = relationship('Payment', backref='invoice', lazy=True, cascade='all, delete-orphan')

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

    invoice_id = Column(String(36), ForeignKey('invoices.id'), nullable=False)
    description = Column(String(500), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), default=0)

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

    invoice_id = Column(String(36), ForeignKey('invoices.id'), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(50))  # CASH, CARD, TRANSFER, INSURANCE
    reference_number = Column(String(100))
    notes = Column(Text)
    payment_date = Column(DateTime, nullable=False)

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

    name = Column(String(200), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    contact_number = Column(String(20))
    email = Column(String(120))
    address = Column(Text)
    is_active = Column(Boolean, default=True)

    def to_dict(self):
        return super().to_dict()


class InsuranceClaim(BaseModel):
    """Insurance claims"""
    __tablename__ = 'insurance_claims'

    invoice_id = Column(String(36), ForeignKey('invoices.id'), nullable=False)
    insurance_provider_id = Column(String(36), ForeignKey('insurance_providers.id'))
    policy_number = Column(String(100))
    claim_number = Column(String(50), unique=True)
    claimed_amount = Column(Numeric(10, 2), default=0)
    approved_amount = Column(Numeric(10, 2), default=0)
    status = Column(String(50), default='PENDING')  # PENDING, SUBMITTED, APPROVED, REJECTED
    claim_date = Column(DateTime)
    settlement_date = Column(DateTime)

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
