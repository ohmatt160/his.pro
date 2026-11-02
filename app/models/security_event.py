from sqlalchemy import Column, ForeignKey, Index, Integer, JSON, String

from app.models.base_model import BaseModel


class SecurityEvent(BaseModel):
    """Privacy-preserving security telemetry for application firewall decisions."""

    __tablename__ = "security_events"
    __table_args__ = (
        Index("idx_security_events_facility_created", "facility_id", "created_at"),
        Index("idx_security_events_subject_created", "subject_hash", "created_at"),
        Index("idx_security_events_action_created", "action", "created_at"),
    )

    facility_id = Column(String(36), ForeignKey("facilities.id"), nullable=True, index=True)
    facility_slug = Column(String(100), ForeignKey("facilities.slug"), nullable=True, index=True)
    subject_hash = Column(String(64), nullable=False, index=True)
    category = Column(String(64), nullable=False, index=True)
    rule_id = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    action = Column(String(20), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    endpoint_hash = Column(String(64), nullable=False)
    response_status = Column(Integer, nullable=True)
    score = Column(Integer, nullable=False, default=0)
    metadata_json = Column(JSON, default=dict)
