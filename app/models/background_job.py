from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint

from app.models.base_model import BaseModel, utc_now


class BackgroundJob(BaseModel):
    """Durable tenant-owned work claimed by a separate worker process."""

    __tablename__ = "background_jobs"
    __table_args__ = (
        UniqueConstraint(
            "facility_id",
            "name",
            "idempotency_key",
            name="uq_background_jobs_tenant_name_idempotency",
        ),
        Index(
            "idx_background_jobs_claim",
            "status",
            "available_at",
            "created_at",
        ),
        Index(
            "idx_background_jobs_tenant_status",
            "facility_id",
            "status",
            "created_at",
        ),
        Index("idx_background_jobs_lease", "status", "locked_at"),
    )

    name = Column(String(100), nullable=False)
    facility_id = Column(String(36), ForeignKey("facilities.id"), nullable=False, index=True)
    requested_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    idempotency_key = Column(String(200), nullable=False)
    payload_json = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default="QUEUED")
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    available_at = Column(DateTime, nullable=False, default=utc_now)
    locked_at = Column(DateTime, nullable=True)
    lock_owner = Column(String(160), nullable=True)
    result_json = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    external_job_id = Column(String(200), nullable=True)

    STATUSES = ("QUEUED", "RUNNING", "COMPLETED", "RETRY", "FAILED")
    NAMES = ("data_migration_import",)
