import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tests.test_app_factory import import_isolated_app


class BackgroundJobIsolationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        database_path = os.path.join(cls.temp_dir.name, "background-jobs.db")
        os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"
        os.environ["BACKGROUND_JOBS_INLINE"] = "false"

        _app, Base, cls.db_session, cls.engine, _httpx = import_isolated_app()
        Base.metadata.create_all(bind=cls.engine)
        from app.services.background_jobs import BackgroundJobService
        from app.models.background_job import BackgroundJob
        from app.models.facility import Facility

        cls.service = BackgroundJobService(inline=False)
        cls.BackgroundJob = BackgroundJob
        cls.Facility = Facility

    @classmethod
    def tearDownClass(cls):
        cls.db_session.remove()
        cls.engine.dispose()
        cls.temp_dir.cleanup()

    def test_job_lookup_is_bound_to_its_facility_and_survives_service_instance(self):
        tenant_a = str(uuid.uuid4())
        tenant_b = str(uuid.uuid4())
        actor_id = str(uuid.uuid4())

        job, created = self.service.enqueue(
            "data_migration_import",
            {"facility_slug": "alpha", "parsed": {}, "summary": {}},
            facility_id=tenant_a,
            requested_by_user_id=actor_id,
            idempotency_key="test:background-job:alpha",
        )

        self.assertTrue(created)
        second_service = type(self.service)(inline=False)
        persisted = second_service.get(job.id, facility_id=tenant_a)
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted.id, job.id)
        self.assertIsNone(second_service.get(job.id, facility_id=tenant_b))
        self.assertIsNone(second_service.get("not-a-uuid", facility_id=tenant_a))
        self.assertEqual(job.facility_id, tenant_a)
        self.assertEqual(job.requested_by_user_id, actor_id)
        self.assertEqual(job.status, "QUEUED")

        replay, replay_created = second_service.enqueue(
            "data_migration_import",
            {"facility_slug": "alpha", "parsed": {}, "summary": {}},
            facility_id=tenant_a,
            requested_by_user_id=actor_id,
            idempotency_key="test:background-job:alpha",
        )
        self.assertFalse(replay_created)
        self.assertEqual(replay.id, job.id)

    def test_enqueue_rejects_non_uuid_ownership(self):
        with self.assertRaisesRegex(ValueError, "immutable UUID"):
            self.service.enqueue(
                "data_migration_import",
                {},
                facility_id="hospital-a",
                requested_by_user_id=str(uuid.uuid4()),
                idempotency_key="test:background-job:invalid",
            )

    def test_storage_purge_is_bound_to_a_purged_facility_and_retries_safely(self):
        facility_id = str(uuid.uuid4())
        facility = self.Facility(
            id=facility_id,
            name="Deleted facility",
            type="hospital",
            slug=f"deleted-{facility_id.replace('-', '')[:20]}",
            canonical_subdomain=f"deleted-{facility_id.replace('-', '')[:20]}",
            is_active=False,
            deletion_status="PURGED",
        )
        self.db_session.add(facility)
        self.db_session.commit()
        job = self.BackgroundJob(
            name="facility_storage_purge",
            facility_id=facility_id,
            requested_by_user_id=str(uuid.uuid4()),
            idempotency_key=f"test:storage-purge:{facility_id}",
            payload_json={"facility_slug": "former-hospital"},
        )
        with patch(
            "app.services.file_upload_service.FileUploadService.delete_tenant_files",
            return_value=True,
        ) as delete_files:
            result = self.service._execute(job, self.db_session)
        delete_files.assert_called_once_with("former-hospital")
        self.assertEqual(result, {"status": "completed", "files_removed": True})

        job.facility_id = str(uuid.uuid4())
        with self.assertRaisesRegex(RuntimeError, "ownership"):
            self.service._execute(job, self.db_session)


if __name__ == "__main__":
    unittest.main()
