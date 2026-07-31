from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)

from app.models.base_model import BaseModel, utc_now


class IntegrationOutbox(BaseModel):
    """Durable tenant-owned work awaiting delivery to an external platform."""

    __tablename__ = "integration_outbox"
    __table_args__ = (
        UniqueConstraint(
            "destination",
            "facility_id",
            "idempotency_key",
            name="uq_integration_outbox_destination_tenant_idempotency",
        ),
        Index(
            "idx_integration_outbox_dispatch",
            "destination",
            "status",
            "available_at",
            "created_at",
        ),
        Index(
            "idx_integration_outbox_tenant_status",
            "facility_id",
            "status",
            "created_at",
        ),
        Index(
            "idx_integration_outbox_lease",
            "status",
            "locked_at",
        ),
    )

    facility_id = Column(
        String(36),
        ForeignKey("facilities.id"),
        nullable=False,
        index=True,
    )
    destination = Column(String(40), nullable=False)
    event_type = Column(String(100), nullable=False)
    aggregate_type = Column(String(80), nullable=True)
    aggregate_id = Column(String(36), nullable=True)
    idempotency_key = Column(String(200), nullable=False)
    correlation_id = Column(String(36), nullable=False)
    payload_json = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default="QUEUED")
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=8)
    available_at = Column(DateTime, nullable=False, default=utc_now)
    locked_at = Column(DateTime, nullable=True)
    lock_owner = Column(String(160), nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    last_error_code = Column(String(80), nullable=True)

    STATUSES = ("QUEUED", "PROCESSING", "RETRY", "DELIVERED", "DEAD")
    DESTINATIONS = ("ohmattos",)
    EVENT_TYPES = (
        "notification.send",
        "analytics.track",
        "logs.error",
        "jobs.submit",
    )
