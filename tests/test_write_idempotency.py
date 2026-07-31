import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

from fastapi import HTTPException


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tests.test_app_factory import import_isolated_app


class WriteIdempotencyServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        database_path = os.path.join(cls.temp_dir.name, "write-idempotency.db")
        os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"

        _app, Base, cls.db_session, cls.engine, _httpx = import_isolated_app()
        Base.metadata.create_all(bind=cls.engine)

        from app.services.write_idempotency_service import WriteIdempotencyService

        cls.service = WriteIdempotencyService

    @classmethod
    def tearDownClass(cls):
        cls.db_session.remove()
        cls.engine.dispose()
        cls.temp_dir.cleanup()

    def test_completed_claim_replays_and_rejects_payload_or_actor_changes(self):
        actor_id = str(uuid.uuid4())
        key = "test:write-idempotency:primary"
        first = self.service.claim(
            facility_slug="alpha-hospital",
            facility_id=str(uuid.uuid4()),
            actor_id=actor_id,
            operation="inventory.stock.update",
            idempotency_key=key,
            payload={"item_id": "item-1", "amount": 10},
        )
        self.assertFalse(first.replay)

        self.service.complete(
            first.record,
            resource_type="inventory",
            resource_id=str(uuid.uuid4()),
            response_status=200,
        )
        self.db_session.commit()

        replay = self.service.claim(
            facility_slug="alpha-hospital",
            actor_id=actor_id,
            operation="inventory.stock.update",
            idempotency_key=key,
            payload={"item_id": "item-1", "amount": 10},
        )
        self.assertTrue(replay.replay)
        self.assertEqual(replay.record.id, first.record.id)

        with self.assertRaisesRegex(ValueError, "different request"):
            self.service.claim(
                facility_slug="alpha-hospital",
                actor_id=actor_id,
                operation="inventory.stock.update",
                idempotency_key=key,
                payload={"item_id": "item-1", "amount": 11},
            )

        with self.assertRaisesRegex(ValueError, "different user"):
            self.service.claim(
                facility_slug="alpha-hospital",
                actor_id=str(uuid.uuid4()),
                operation="inventory.stock.update",
                idempotency_key=key,
                payload={"item_id": "item-1", "amount": 10},
            )

    def test_key_scope_is_per_tenant_and_invalid_keys_fail_closed(self):
        key = "test:write-idempotency:tenant-scope"
        alpha = self.service.claim(
            facility_slug="alpha-hospital",
            actor_id=str(uuid.uuid4()),
            operation="alerts.create",
            idempotency_key=key,
            payload={"title": "Alpha"},
        )
        beta = self.service.claim(
            facility_slug="beta-hospital",
            actor_id=str(uuid.uuid4()),
            operation="alerts.create",
            idempotency_key=key,
            payload={"title": "Beta"},
        )
        self.assertNotEqual(alpha.record.id, beta.record.id)
        self.db_session.rollback()

        with self.assertRaises(HTTPException) as error:
            self.service.claim(
                facility_slug="alpha-hospital",
                operation="alerts.create",
                idempotency_key="short",
                payload={},
            )
        self.assertEqual(error.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
