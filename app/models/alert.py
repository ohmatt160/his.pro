from datetime import datetime
from app.extensions import db
from app.models.base_model import BaseModel

class Alert(BaseModel):
    """Alert model for system notifications and alerts"""
    __tablename__ = 'alerts'
    
    facility_slug = db.Column(db.String(100), db.ForeignKey('facilities.slug'), nullable=False, index=True)
    alert_type = db.Column(db.String(50), nullable=False, index=True)  # info/warning/critical
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    recipient_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True, index=True)
    is_read = db.Column(db.Boolean, default=False, index=True)
    read_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    recipient = db.relationship('User', backref='alerts', lazy=True)
    
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