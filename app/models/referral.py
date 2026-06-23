from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index

from app.models.base_model import BaseModel


class Referral(BaseModel):
    """Department-to-department patient referral within one facility."""
    __tablename__ = "referrals"
    __table_args__ = (
        Index('idx_referrals_facility_to_status', 'facility_slug', 'to_department_id', 'status'),
        Index('idx_referrals_facility_patient_created', 'facility_slug', 'patient_id', 'created_at'),
    )

    facility_id = Column(String(36), ForeignKey("facilities.id"), nullable=True, index=True)
    facility_slug = Column(String(100), ForeignKey("facilities.slug"), nullable=False, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    from_department_id = Column(String(36), nullable=True, index=True)
    to_department_id = Column(String(36), nullable=False, index=True)
    reason = Column(String(255), nullable=False)
    priority = Column(String(20), default="routine")
    notes = Column(Text)
    status = Column(String(20), default="pending")
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    accepted_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    completed_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    STATUSES = ["pending", "accepted", "completed", "cancelled"]
    PRIORITIES = ["routine", "urgent", "emergency"]
