from datetime import datetime

from app.extensions import db_session
from app.models.order_workflow import OrderWorkflowEvent
from app.utils.validators import Validators


class OrderWorkflowService:
    """Record durable order workflow events."""

    @staticmethod
    def record(
        *,
        facility_slug: str,
        order_type: str,
        order_id: str,
        event_type: str,
        status: str,
        title: str,
        patient_id: str | None = None,
        message: str | None = None,
        actor_id: str | None = None,
        target_role: str | None = None,
        metadata: dict | None = None,
    ) -> OrderWorkflowEvent:
        event = OrderWorkflowEvent(
            facility_slug=facility_slug,
            patient_id=patient_id,
            order_type=order_type,
            order_id=order_id,
            event_type=event_type,
            status=status,
            title=Validators.sanitize_string(title),
            message=Validators.sanitize_string(message) if message else None,
            actor_id=actor_id,
            target_role=target_role,
            metadata_json=metadata or {},
            occurred_at=datetime.utcnow(),
        )
        db_session.add(event)
        db_session.flush()
        return event

