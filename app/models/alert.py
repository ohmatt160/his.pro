from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel


class Alert(BaseModel):
    """Alert model for system notifications and alerts"""
    __tablename__ = 'alerts'

    facility_slug = Column(String(100), ForeignKey('facilities.slug'), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False, index=True)  # info/warning/critical
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    recipient_id = Column(String(36), ForeignKey('users.id'), nullable=True, index=True)
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    recipient = relationship('User', backref='alerts', lazy=True)

    # Alert types
    ALERT_TYPES = ['info', 'warning', 'critical']

    def to_dict(self):
        """Convert to dictionary"""
        data = super().to_dict()
        return data

    def mark_as_read(self):
        """Mark alert as read"""
        self.is_read = True
        self.read_at = datetime.utcnow()
        return self

    def mark_as_unread(self):
        """Mark alert as unread"""
        self.is_read = False
        self.read_at = None
        return self

    @property
    def is_expired(self):
        """Check if alert has expired"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
