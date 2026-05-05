from datetime import datetime
from app.extensions import db
from app.models.base_model import BaseModel

class AuditLog(BaseModel):
    """Audit log model for tracking user actions"""
    __tablename__ = 'audit_logs'
    
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.String(36))
    details = db.Column(db.JSON, default=dict)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    
    user = db.relationship('User', backref='audit_logs')
    
    def to_dict(self):
        data = super().to_dict()
        if self.user:
            data['user'] = {
                'id': self.user.id,
                'username': self.user.username,
                'email': self.user.email
            }
        return data
