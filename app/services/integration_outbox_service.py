from __future__ import annotations

import json
import logging
import random
import re
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.extensions import SessionLocal, db_session
from app.models.base_model import utc_now
from app.models.integration_outbox import IntegrationOutbox
from app.services.ohmattos_client import OhmattOSClient, ohmattos_client

logger = logging.getLogger(__name__)

MAX_OUTBOX_PAYLOAD_BYTES = 64 * 1024
MAX_BATCH_SIZE = 100
IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._~:/-]{0,199}$")


@dataclass(frozen=True)
class OutboxDispatchSummary:
    claimed: int = 0
    delivered: int = 0
    retried: int = 0
    dead: int = 0


class IntegrationOutboxService:
    """Transactional enqueue and horizontally safe external dispatch."""

    @staticmethod
    def enqueue(
        *,
        facility_id: str,
        event_type: str,
        payload: dict[str, Any],
        idempotency_key: str,
        aggregate_type: str | None = None,
        aggregate_id: str | None = None,
        correlation_id: str | None = None,
        max_attempts: int = 8,
        session: Session | None = None,
    ) -> IntegrationOutbox:
        session = session or db_session
        tenant_id = IntegrationOutboxService._canonical_uuid(
            facility_id, "facility_id"
        )
        if event_type not in IntegrationOutbox.EVENT_TYPES:
            raise ValueError("unsupported integration outbox event type")
        if not isinstance(idempotency_key, str) or not IDEMPOTENCY_KEY_PATTERN.fullmatch(
            idempotency_key
        ):
            raise ValueError("idempotency_key contains unsupported characters")
        if not 1 <= max_attempts <= 20:
            raise ValueError("max_attempts must be between 1 and 20")
        if "tenant_id" in payload or "app_id" in payload:
            raise ValueError("outbox payload must not carry caller-selected ownership")
        try:
            serialized = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("outbox payload must be JSON serializable") from exc
        if len(serialized) > MAX_OUTBOX_PAYLOAD_BYTES:
            raise ValueError("outbox payload exceeds the safe size limit")

        row = IntegrationOutbox(
            facility_id=tenant_id,
            destination="ohmattos",
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            idempotency_key=idempotency_key,
            correlation_id=IntegrationOutboxService._canonical_uuid(
                correlation_id or str(uuid.uuid4()), "correlation_id"
            ),
            payload_json=payload,
            status="QUEUED",
            attempts=0,
            max_attempts=max_attempts,
            available_at=utc_now(),
        )
        session.add(row)
        return row

    @staticmethod
    def dispatch_batch(
        *,
        worker_id: str,
        client: OhmattOSClient = ohmattos_client,
        batch_size: int = 25,
        lease_seconds: int = 120,
    ) -> OutboxDispatchSummary:
        if not worker_id or len(worker_id) > 160:
            raise ValueError("worker_id must contain between 1 and 160 characters")
        if not 1 <= batch_size <= MAX_BATCH_SIZE:
            raise ValueError(f"batch_size must be between 1 and {MAX_BATCH_SIZE}")
        if not 30 <= lease_seconds <= 900:
            raise ValueError("lease_seconds must be between 30 and 900")

        feature_events = {
            "notifications": "notification.send",
            "analytics": "analytics.track",
            "logs": "logs.error",
            "jobs": "jobs.submit",
        }
        enabled_event_types = tuple(
            event_type
            for feature, event_type in feature_events.items()
            if client.feature_enabled(feature)
        )
        if not enabled_event_types:
            return OutboxDispatchSummary()

        claimed_ids = IntegrationOutboxService._claim_batch(
            worker_id=worker_id,
            batch_size=batch_size,
            lease_seconds=lease_seconds,
            event_types=enabled_event_types,
        )
        delivered = retried = dead = 0
        for outbox_id in claimed_ids:
            outcome = IntegrationOutboxService._dispatch_one(
                outbox_id=outbox_id,
                worker_id=worker_id,
                client=client,
            )
            if outcome == "DELIVERED":
                delivered += 1
            elif outcome == "RETRY":
                retried += 1
            elif outcome == "DEAD":
                dead += 1

        return OutboxDispatchSummary(
            claimed=len(claimed_ids),
            delivered=delivered,
            retried=retried,
            dead=dead,
        )

    @staticmethod
    def _claim_batch(
        *,
        worker_id: str,
        batch_size: int,
        lease_seconds: int,
        event_types: tuple[str, ...] | None = None,
    ) -> list[str]:
        session = SessionLocal()
        try:
            now = utc_now()
            stale_before = now - timedelta(seconds=lease_seconds)
            query = (
                session.query(IntegrationOutbox)
                .filter(
                    IntegrationOutbox.destination == "ohmattos",
                    *(
                        [IntegrationOutbox.event_type.in_(event_types)]
                        if event_types
                        else []
                    ),
                    or_(
                        and_(
                            IntegrationOutbox.status.in_(("QUEUED", "RETRY")),
                            IntegrationOutbox.available_at <= now,
                        ),
                        and_(
                            IntegrationOutbox.status == "PROCESSING",
                            IntegrationOutbox.locked_at < stale_before,
                        ),
                    ),
                )
                .order_by(
                    IntegrationOutbox.available_at.asc(),
                    IntegrationOutbox.created_at.asc(),
                )
            )
            if session.bind and session.bind.dialect.name == "postgresql":
                query = query.with_for_update(skip_locked=True)
            rows = query.limit(batch_size).all()
            ids = []
            for row in rows:
                row.status = "PROCESSING"
                row.locked_at = now
                row.lock_owner = worker_id
                row.updated_at = now
                ids.append(str(row.id))
            session.commit()
            return ids
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _dispatch_one(
        *,
        outbox_id: str,
        worker_id: str,
        client: OhmattOSClient,
    ) -> str | None:
        snapshot_session = SessionLocal()
        try:
            row = (
                snapshot_session.query(IntegrationOutbox)
                .filter_by(
                    id=outbox_id,
                    status="PROCESSING",
                    lock_owner=worker_id,
                )
                .first()
            )
            if not row:
                return None
            snapshot = {
                "facility_id": str(row.facility_id),
                "event_type": row.event_type,
                "idempotency_key": row.idempotency_key,
                "payload": dict(row.payload_json or {}),
            }
        finally:
            snapshot_session.close()

        result = IntegrationOutboxService._deliver_snapshot(snapshot, client)
        update_session = SessionLocal()
        try:
            row = (
                update_session.query(IntegrationOutbox)
                .filter_by(
                    id=outbox_id,
                    status="PROCESSING",
                    lock_owner=worker_id,
                )
                .first()
            )
            if not row:
                return None

            now = utc_now()
            row.attempts = int(row.attempts or 0) + 1
            row.locked_at = None
            row.lock_owner = None
            row.updated_at = now
            if result.get("ok"):
                row.status = "DELIVERED"
                row.delivered_at = now
                row.last_error_code = None
            else:
                status_code = result.get("status")
                row.last_error_code = (
                    f"http_{status_code}" if status_code else "transport_unavailable"
                )
                retryable = bool(result.get("retryable"))
                if retryable and row.attempts < row.max_attempts:
                    row.status = "RETRY"
                    row.available_at = now + timedelta(
                        seconds=IntegrationOutboxService._retry_delay_seconds(
                            row.attempts
                        )
                    )
                else:
                    row.status = "DEAD"
            outcome = row.status
            update_session.commit()
            return outcome
        except Exception:
            update_session.rollback()
            raise
        finally:
            update_session.close()

    @staticmethod
    def _deliver_snapshot(
        snapshot: dict[str, Any],
        client: OhmattOSClient,
    ) -> dict[str, Any]:
        tenant_id = snapshot["facility_id"]
        event_type = snapshot["event_type"]
        payload = dict(snapshot["payload"])
        payload.setdefault("idempotency_key", snapshot["idempotency_key"])

        if event_type == "notification.send":
            if not client.feature_enabled("notifications"):
                return {
                    "ok": False,
                    "error": "notification delivery is disabled",
                    "retryable": True,
                }
            allowed = {
                "user_id",
                "channel_type",
                "recipient",
                "subject",
                "body",
                "template_id",
                "idempotency_key",
            }
            if set(payload) - allowed:
                return {
                    "ok": False,
                    "error": "notification outbox payload is invalid",
                    "retryable": False,
                }
            return client.send_notification(tenant_id=tenant_id, **payload)

        if event_type == "analytics.track":
            if not client.feature_enabled("analytics"):
                return {"ok": False, "error": "analytics disabled", "retryable": True}
            if set(payload) - {
                "event_name",
                "properties",
                "user_id",
                "idempotency_key",
            }:
                return {
                    "ok": False,
                    "error": "analytics outbox payload is invalid",
                    "retryable": False,
                }
            return client.track_event(tenant_id=tenant_id, **payload)

        if event_type == "logs.error":
            if not client.feature_enabled("logs"):
                return {"ok": False, "error": "logs disabled", "retryable": True}
            if set(payload) - {
                "message",
                "severity",
                "context",
                "request_id",
                "user_id",
                "idempotency_key",
            }:
                return {
                    "ok": False,
                    "error": "log outbox payload is invalid",
                    "retryable": False,
                }
            return client.report_error(tenant_id=tenant_id, **payload)

        if event_type == "jobs.submit":
            if not client.feature_enabled("jobs"):
                return {"ok": False, "error": "jobs disabled", "retryable": True}
            if set(payload) - {
                "job_type",
                "payload",
                "priority",
                "max_attempts",
                "idempotency_key",
            }:
                return {
                    "ok": False,
                    "error": "job outbox payload is invalid",
                    "retryable": False,
                }
            return client.submit_job(tenant_id=tenant_id, **payload)

        return {
            "ok": False,
            "error": "unsupported outbox event",
            "retryable": False,
        }

    @staticmethod
    def _retry_delay_seconds(attempt: int) -> int:
        base = min(15 * (2 ** max(attempt - 1, 0)), 3600)
        return base + random.randint(0, max(1, base // 4))

    @staticmethod
    def _canonical_uuid(value: str, field: str) -> str:
        try:
            return str(uuid.UUID(str(value)))
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError(f"{field} must be a UUID") from exc
