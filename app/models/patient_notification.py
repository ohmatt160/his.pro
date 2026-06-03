from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship

from app.models.base_model import BaseModel


class PatientNotification(BaseModel):
    """Patient-facing portal/SMS notification queue."""

    __tablename__ = "patient_notifications"

    facility_slug = Column(String(100), ForeignKey("facilities.slug"), nullable=False, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    notification_type = Column(String(80), nullable=False, index=True)
    channel = Column(String(30), nullable=False, default="PORTAL")
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    recipient_phone = Column(String(30), nullable=True)
    recipient_email = Column(String(120), nullable=True)
    status = Column(String(30), nullable=False, default="QUEUED", index=True)
    source_type = Column(String(80), nullable=True, index=True)
    source_id = Column(String(36), nullable=True, index=True)
    metadata_json = Column(JSON, default=dict)
    sent_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)

    patient = relationship("Patient", backref="notifications", lazy=True)

    STATUSES = ["QUEUED", "SENT", "SUPPRESSED", "FAILED", "READ"]
    CHANNELS = ["PORTAL", "SMS"]

