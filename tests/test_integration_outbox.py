import sys
import unittest
import uuid
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.models  # noqa: E402,F401
from app.extensions import Base  # noqa: E402
from app.models.audit_log import AuditLog  # noqa: E402
from app.models.base_model import utc_now  # noqa: E402
from app.models.facility import Facility  # noqa: E402
from app.models.integration_outbox import IntegrationOutbox  # noqa: E402
from app.services.audit_log_service import AuditLogService  # noqa: E402
from app.services.integration_outbox_service import (  # noqa: E402
    IntegrationOutboxService,
)


class FakeOhmattOSClient:
    def __init__(self, results=None, enabled_features=None):
        self.results = list(results or [{"ok": True, "status": 202, "data": {}}])
        self.enabled_features = set(enabled_features or {"notifications"})
        self.notifications = []
        self.analytics_events = []
        self.error_logs = []
        self.jobs = []

    def feature_enabled(self, feature):
        return feature in self.enabled_features

    def send_notification(self, **kwargs):
        self.notifications.append(kwargs)
        return self._next_result()

    def track_event(self, **kwargs):
        self.analytics_events.append(kwargs)
        return self._next_result()

    def report_error(self, **kwargs):
        self.error_logs.append(kwargs)
        return self._next_result()

    def submit_job(self, **kwargs):
        self.jobs.append(kwargs)
        return self._next_result()

    def _next_result(self):
        if len(self.results) > 1:
            return self.results.pop(0)
        return self.results[0]


class IntegrationOutboxTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.session_local_patch = patch.dict(
            IntegrationOutboxService._claim_batch.__globals__,
            {"SessionLocal": self.Session},
        )
        self.session_local_patch.start()
        self.addCleanup(self.session_local_patch.stop)

        self.tenant_a = str(uuid.uuid4())
        self.tenant_b = str(uuid.uuid4())
        session = self.Session()
        session.add_all(
            [
                Facility(
                    id=self.tenant_a,
                    name="Hospital A",
                    type="hospital",
                    slug="hospital-a",
                ),
                Facility(
                    id=self.tenant_b,
                    name="Hospital B",
                    type="hospital",
                    slug="hospital-b",
                ),
            ]
        )
        session.commit()
        session.close()

    def tearDown(self):
        self.engine.dispose()

    @staticmethod
    def notification_payload(idempotency_key):
        return {
            "user_id": "patient:opaque-id",
            "channel_type": "sms",
            "recipient": "+2348012345678",
            "subject": "",
            "body": "Your prescription is ready.",
            "template_id": None,
            "idempotency_key": idempotency_key,
        }

    def enqueue(self, session, tenant_id, idempotency_key):
        return IntegrationOutboxService.enqueue(
            facility_id=tenant_id,
            event_type="notification.send",
            payload=self.notification_payload(idempotency_key),
            idempotency_key=idempotency_key,
            aggregate_type="patient_notification",
            aggregate_id=str(uuid.uuid4()),
            session=session,
        )

    def test_outbox_row_rolls_back_with_the_hospital_transaction(self):
        session = self.Session()
        self.enqueue(session, self.tenant_a, "notice:rollback")
        session.flush()
        self.assertEqual(session.query(IntegrationOutbox).count(), 1)
        session.rollback()
        self.assertEqual(session.query(IntegrationOutbox).count(), 0)
        session.close()

    def test_audit_and_analytics_outbox_roll_back_atomically(self):
        session = self.Session()
        with patch.dict(
            AuditLogService.log_action.__globals__,
            {"db": SimpleNamespace(session=session)},
        ):
            audit = AuditLogService.log_action(
                user_id=str(uuid.uuid4()),
                action="GET_PATIENTS",
                resource_type="patients",
                facility_slug="hospital-a",
                commit=False,
            )
        self.assertIsNotNone(audit)
        IntegrationOutboxService.enqueue(
            facility_id=self.tenant_a,
            event_type="analytics.track",
            aggregate_type="audit_log",
            aggregate_id=audit.id,
            idempotency_key=f"hispro:analytics:{audit.id}",
            payload={
                "event_name": "hispro.get.patients",
                "properties": {"event_id": audit.id},
            },
            session=session,
        )
        session.rollback()
        self.assertEqual(session.query(AuditLog).count(), 0)
        self.assertEqual(session.query(IntegrationOutbox).count(), 0)
        session.close()

    def test_idempotency_is_composite_with_tenant(self):
        session = self.Session()
        self.enqueue(session, self.tenant_a, "notice:same-key")
        self.enqueue(session, self.tenant_b, "notice:same-key")
        session.commit()
        self.assertEqual(session.query(IntegrationOutbox).count(), 2)

        self.enqueue(session, self.tenant_a, "notice:same-key")
        with self.assertRaises(IntegrityError):
            session.commit()
        session.rollback()
        session.close()

    def test_payload_cannot_select_application_or_tenant(self):
        session = self.Session()
        with self.assertRaisesRegex(ValueError, "ownership"):
            IntegrationOutboxService.enqueue(
                facility_id=self.tenant_a,
                event_type="notification.send",
                payload={"tenant_id": self.tenant_b},
                idempotency_key="notice:forged-tenant",
                session=session,
            )
        with self.assertRaisesRegex(ValueError, "ownership"):
            IntegrationOutboxService.enqueue(
                facility_id=self.tenant_a,
                event_type="notification.send",
                payload={"app_id": str(uuid.uuid4())},
                idempotency_key="notice:forged-app",
                session=session,
            )
        session.close()

    def test_enqueue_rejects_unsafe_keys_and_non_json_payloads(self):
        session = self.Session()
        with self.assertRaisesRegex(ValueError, "unsupported characters"):
            IntegrationOutboxService.enqueue(
                facility_id=self.tenant_a,
                event_type="analytics.track",
                payload={"event_name": "patient.updated"},
                idempotency_key="valid-prefix\r\nInjected: header",
                session=session,
            )
        with self.assertRaisesRegex(ValueError, "JSON serializable"):
            IntegrationOutboxService.enqueue(
                facility_id=self.tenant_a,
                event_type="analytics.track",
                payload={"event_name": "patient.updated", "value": object()},
                idempotency_key="analytics:strict-json",
                session=session,
            )
        session.close()

    def test_dispatch_uses_row_tenant_and_marks_delivery(self):
        session = self.Session()
        row = self.enqueue(session, self.tenant_a, "notice:deliver")
        session.commit()
        row_id = row.id
        session.close()

        client = FakeOhmattOSClient()
        summary = IntegrationOutboxService.dispatch_batch(
            worker_id="worker-a",
            client=client,
        )

        self.assertEqual(summary.claimed, 1)
        self.assertEqual(summary.delivered, 1)
        self.assertEqual(client.notifications[0]["tenant_id"], self.tenant_a)
        self.assertNotIn("app_id", client.notifications[0])

        session = self.Session()
        delivered = session.query(IntegrationOutbox).filter_by(id=row_id).one()
        self.assertEqual(delivered.status, "DELIVERED")
        self.assertEqual(delivered.attempts, 1)
        self.assertIsNotNone(delivered.delivered_at)
        self.assertIsNone(delivered.lock_owner)
        session.close()

    def test_retry_keeps_tenant_context_and_eventually_delivers(self):
        session = self.Session()
        row = self.enqueue(session, self.tenant_a, "notice:retry")
        session.commit()
        row_id = row.id
        session.close()

        client = FakeOhmattOSClient(
            results=[
                {
                    "ok": False,
                    "status": 503,
                    "error": "unavailable",
                    "retryable": True,
                },
                {"ok": True, "status": 202, "data": {}},
            ]
        )
        with patch.object(
            IntegrationOutboxService,
            "_retry_delay_seconds",
            return_value=1,
        ):
            first = IntegrationOutboxService.dispatch_batch(
                worker_id="worker-a",
                client=client,
            )
        self.assertEqual(first.retried, 1)

        session = self.Session()
        retry = session.query(IntegrationOutbox).filter_by(id=row_id).one()
        self.assertEqual(retry.status, "RETRY")
        self.assertEqual(retry.last_error_code, "http_503")
        retry.available_at = utc_now() - timedelta(seconds=1)
        session.commit()
        session.close()

        second = IntegrationOutboxService.dispatch_batch(
            worker_id="worker-b",
            client=client,
        )
        self.assertEqual(second.delivered, 1)
        self.assertEqual(
            [notice["tenant_id"] for notice in client.notifications],
            [self.tenant_a, self.tenant_a],
        )

    def test_live_lease_cannot_be_claimed_by_a_second_worker(self):
        session = self.Session()
        self.enqueue(session, self.tenant_a, "notice:lease")
        session.commit()
        session.close()

        first = IntegrationOutboxService._claim_batch(
            worker_id="worker-a",
            batch_size=10,
            lease_seconds=120,
        )
        second = IntegrationOutboxService._claim_batch(
            worker_id="worker-b",
            batch_size=10,
            lease_seconds=120,
        )
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])

        session = self.Session()
        row = session.query(IntegrationOutbox).filter_by(id=first[0]).one()
        row.locked_at = utc_now() - timedelta(seconds=121)
        session.commit()
        session.close()

        recovered = IntegrationOutboxService._claim_batch(
            worker_id="worker-b",
            batch_size=10,
            lease_seconds=120,
        )
        self.assertEqual(recovered, first)

    def test_delivery_uses_the_outbox_idempotency_key_for_every_event_type(self):
        client = FakeOhmattOSClient(
            enabled_features={"analytics", "logs", "jobs"},
        )
        cases = [
            (
                "analytics.track",
                {"event_name": "patient.updated", "properties": {}},
                client.analytics_events,
            ),
            (
                "logs.error",
                {"message": "delivery failed", "severity": "error"},
                client.error_logs,
            ),
            (
                "jobs.submit",
                {
                    "job_type": "delay",
                    "payload": {"duration_ms": 1},
                    "priority": 5,
                    "max_attempts": 3,
                },
                client.jobs,
            ),
        ]

        for index, (event_type, payload, calls) in enumerate(cases):
            idempotency_key = f"outbox:event:{index}"
            result = IntegrationOutboxService._deliver_snapshot(
                {
                    "facility_id": self.tenant_a,
                    "event_type": event_type,
                    "idempotency_key": idempotency_key,
                    "payload": payload,
                },
                client,
            )
            self.assertTrue(result["ok"])
            self.assertEqual(calls[-1]["tenant_id"], self.tenant_a)
            self.assertEqual(calls[-1]["idempotency_key"], idempotency_key)


if __name__ == "__main__":
    unittest.main()
