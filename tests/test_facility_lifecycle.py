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


class FacilityLifecycleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        os.environ["DATABASE_URL"] = f"sqlite:///{cls.temp_dir.name}/facility-lifecycle.db"
        os.environ["APP_ENV"] = "development"
        os.environ["TESTING"] = "true"
        app, Base, cls.db_session, cls.engine, _httpx = import_isolated_app()
        Base.metadata.create_all(bind=cls.engine)
        from app.models.background_job import BackgroundJob
        from app.models.facility import Facility
        from app.models.user import User
        from app.services.facility_lifecycle_service import FacilityLifecycleService

        cls.BackgroundJob = BackgroundJob
        cls.Facility = Facility
        cls.User = User
        cls.service = FacilityLifecycleService

    @classmethod
    def tearDownClass(cls):
        cls.db_session.remove()
        cls.engine.dispose()
        cls.temp_dir.cleanup()

    def make_facility_and_admin(self):
        unique = uuid.uuid4().hex[:12]
        facility = self.Facility(
            name=f"North Clinic {unique}",
            type="clinic",
            slug=f"north-clinic-{unique}",
            modules=[],
            settings={},
            is_active=True,
        )
        self.db_session.add(facility)
        self.db_session.flush()
        admin = self.User(
            username=f"admin-{unique}",
            email=f"admin-{unique}@example.test",
            role="ADMIN",
            facility_id=facility.id,
            facility_slug=facility.slug,
            is_active=True,
        )
        admin.set_password("correct-password")
        self.db_session.add(admin)
        self.db_session.commit()
        return facility, admin

    def test_deletion_is_recoverable_and_recovery_secret_is_fragment_only(self):
        facility, admin = self.make_facility_and_admin()
        with patch(
            "app.services.facility_lifecycle_service.EmailService.send_email",
            return_value=(True, "sent"),
        ) as send_email:
            result = self.service.request_deletion(
                self.db_session,
                facility=facility,
                actor=admin,
                password="correct-password",
                confirmation_name=facility.name,
            )

        self.assertEqual(result["status"], "pending_deletion")
        self.assertFalse(facility.is_active)
        self.assertTrue(result["recovery_token"])
        email_body = send_email.call_args.args[2]
        self.assertIn("#token=", email_body)
        self.assertNotIn("&token=", email_body)

        recovered = self.service.recover_deletion(
            self.db_session,
            facility=facility,
            recovery_token=result["recovery_token"],
        )
        job = (
            self.db_session.query(self.BackgroundJob)
            .filter_by(name="facility_deletion_purge", facility_id=facility.id)
            .one()
        )
        self.assertEqual(recovered["status"], "active")
        self.assertTrue(facility.is_active)
        self.assertEqual(job.status, "CANCELLED")

    def test_wrong_password_or_facility_name_cannot_schedule_deletion(self):
        facility, admin = self.make_facility_and_admin()
        from fastapi import HTTPException

        for password, name, status_code in (
            ("wrong-password", facility.name, 403),
            ("correct-password", "Other Clinic", 400),
        ):
            with self.assertRaises(HTTPException) as raised:
                self.service.request_deletion(
                    self.db_session,
                    facility=facility,
                    actor=admin,
                    password=password,
                    confirmation_name=name,
                )
            self.assertEqual(raised.exception.status_code, status_code)
            self.db_session.rollback()
            self.assertTrue(facility.is_active)


if __name__ == "__main__":
    unittest.main()
