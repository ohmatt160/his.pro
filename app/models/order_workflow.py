from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, Text, Index

from app.models.base_model import BaseModel


class OrderWorkflowEvent(BaseModel):
    """Append-only clinical order workflow status event."""

    __tablename__ = "order_workflow_events"
    __table_args__ = (
        Index("idx_order_workflow_facility_occurred", "facility_slug", "occurred_at"),
        Index("idx_order_workflow_facility_order", "facility_slug", "order_type", "order_id"),
        Index("idx_order_workflow_facility_role_status", "facility_slug", "target_role", "status"),
    )

    facility_id = Column(String(36), ForeignKey("facilities.id"), nullable=True, index=True)
    facility_slug = Column(String(100), ForeignKey("facilities.slug"), nullable=False, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=True, index=True)
    order_type = Column(String(80), nullable=False, index=True)
    order_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    status = Column(String(80), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=True)
    actor_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    target_role = Column(String(80), nullable=True, index=True)
    metadata_json = Column(JSON, default=dict)
    occurred_at = Column(DateTime, nullable=False)
