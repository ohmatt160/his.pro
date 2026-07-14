from datetime import datetime
from sqlalchemy import Column, String, JSON, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel


class AuditLog(BaseModel):
    """Audit log model for tracking user actions"""
    __tablename__ = 'audit_logs'
    __table_args__ = (
        Index('idx_audit_logs_facility_created', 'facility_slug', 'created_at'),
        Index('idx_audit_logs_facility_user_created', 'facility_slug', 'user_id', 'created_at'),
        Index('idx_audit_logs_facility_action_created', 'facility_slug', 'action', 'created_at'),
        Index('idx_audit_logs_facility_resource_created', 'facility_slug', 'resource_type', 'resource_id', 'created_at'),
    )

    user_id = Column(String(36), ForeignKey('users.id'))
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(String(36))
    facility_id = Column(String(36), ForeignKey('facilities.id'), nullable=True, index=True)
    facility_slug = Column(String(100), ForeignKey('facilities.slug'), nullable=True, index=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(45))
    user_agent = Column(String(500))

    user = relationship('User', backref='audit_logs')

    def to_dict(self):
        data = super().to_dict()
        if self.user:
            data['user'] = {
                'id': self.user.id,
                'username': self.user.username,
                'email': self.user.email
            }
        return data
