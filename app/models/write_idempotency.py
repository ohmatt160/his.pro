from sqlalchemy import Column, ForeignKey, Index, Integer, JSON, String

from app.models.base_model import BaseModel


class WriteIdempotencyRecord(BaseModel):
    """Durable replay guard for state-changing API operations."""

    __tablename__ = "write_idempotency_records"
    __table_args__ = (
        Index(
            "uq_write_idempotency_facility_operation_key",
            "facility_slug",
            "operation",
            "idempotency_key",
            unique=True,
        ),
        Index(
            "idx_write_idempotency_facility_created",
            "facility_slug",
            "created_at",
        ),
    )

    facility_id = Column(
        String(36),
        ForeignKey("facilities.id"),
        nullable=True,
        index=True,
    )
    facility_slug = Column(
        String(100),
        ForeignKey("facilities.slug"),
        nullable=False,
        index=True,
    )
    actor_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    operation = Column(String(120), nullable=False)
    idempotency_key = Column(String(200), nullable=False)
    payload_hash = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, default="IN_PROGRESS", index=True)
    resource_type = Column(String(80), nullable=True)
    resource_id = Column(String(36), nullable=True, index=True)
    resource_ids = Column(JSON, nullable=True)
    response_status = Column(Integer, nullable=True)

    STATUSES = ("IN_PROGRESS", "COMPLETED")
