import os
import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class OhmattOSIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.original = {
            key: os.environ.get(key)
            for key in (
                "OHMATTOS_ENABLED",
                "OHMATTOS_URL",
                "OHMATTOS_API_KEY",
                "OHMATTOS_APP_ID",
                "OHMATTOS_JOBS_ENABLED",
                "HISPRO_PATIENT_NOTIFICATION_CHANNELS",
            )
        }

    def tearDown(self):
        for key, value in self.original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_disabled_client_never_raises_or_posts(self):
        from app.services.ohmattos_client import OhmattOSClient

        os.environ["OHMATTOS_ENABLED"] = "false"
        client = OhmattOSClient()
        result = client.submit_job("hispro.test", {"safe": True})
        self.assertFalse(result["ok"])
        self.assertIn("disabled", result["error"].lower())

    def test_feature_flags_require_global_enable_and_feature_enable(self):
        from app.services.ohmattos_client import OhmattOSClient

        os.environ["OHMATTOS_ENABLED"] = "true"
        os.environ["OHMATTOS_URL"] = "http://127.0.0.1:9000"
        os.environ["OHMATTOS_API_KEY"] = "test-key"
        os.environ["OHMATTOS_JOBS_ENABLED"] = "false"
        client = OhmattOSClient()
        self.assertFalse(client.feature_enabled("jobs"))

        os.environ["OHMATTOS_JOBS_ENABLED"] = "true"
        client = OhmattOSClient()
        self.assertTrue(client.feature_enabled("jobs"))

    def test_notification_requires_app_id(self):
        from app.services.ohmattos_client import OhmattOSClient

        os.environ["OHMATTOS_ENABLED"] = "true"
        os.environ["OHMATTOS_URL"] = "http://127.0.0.1:9000"
        os.environ["OHMATTOS_API_KEY"] = "test-key"
        os.environ.pop("OHMATTOS_APP_ID", None)
        client = OhmattOSClient()
        result = client.send_notification(
            user_id="patient:1",
            channel_type="sms",
            recipient="+2348012345678",
            subject="",
            body="Hi",
            idempotency_key="notification-1",
        )
        self.assertFalse(result["ok"])
        self.assertIn("APP_ID", result["error"])

    def test_email_notification_matches_ohmattos_worker_contract(self):
        from app.services.ohmattos_client import OhmattOSClient

        os.environ["OHMATTOS_ENABLED"] = "true"
        os.environ["OHMATTOS_URL"] = "http://127.0.0.1:9000"
        os.environ["OHMATTOS_API_KEY"] = "test-key"
        os.environ["OHMATTOS_APP_ID"] = "his-pro-app-id"
        client = OhmattOSClient()
        captured = {}

        def capture(path, payload):
            captured["path"] = path
            captured["payload"] = payload
            return {"ok": True, "status": 202, "data": {"status": "queued"}}

        client._post = capture
        result = client.send_notification(
            user_id="patient:1",
            channel_type="EMAIL",
            recipient="patient@example.com",
            subject="Appointment reminder",
            body="Your appointment is tomorrow.",
            idempotency_key="hispro:patient-notification:email-1",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(captured["path"], "/api/v1/notifications/send")
        self.assertEqual(captured["payload"]["channel_type"], "email")
        self.assertEqual(
            captured["payload"]["content"],
            {
                "to": "patient@example.com",
                "subject": "Appointment reminder",
                "body": "Your appointment is tomorrow.",
            },
        )
        self.assertEqual(
            captured["payload"]["idempotency_key"],
            "hispro:patient-notification:email-1",
        )
        self.assertNotIn("facility_slug", captured["payload"]["content"])
        self.assertNotIn("patient_id", captured["payload"]["content"])

    def test_sms_notification_matches_ohmattos_worker_contract(self):
        from app.services.ohmattos_client import OhmattOSClient

        os.environ["OHMATTOS_ENABLED"] = "true"
        os.environ["OHMATTOS_URL"] = "http://127.0.0.1:9000"
        os.environ["OHMATTOS_API_KEY"] = "test-key"
        os.environ["OHMATTOS_APP_ID"] = "his-pro-app-id"
        client = OhmattOSClient()
        captured = {}

        def capture(path, payload):
            captured["path"] = path
            captured["payload"] = payload
            return {"ok": True, "status": 202, "data": {"status": "queued"}}

        client._post = capture
        result = client.send_notification(
            user_id="patient:1",
            channel_type="sms",
            recipient="+2348012345678",
            subject="Ignored for SMS",
            body="Your prescription is ready.",
            idempotency_key="hispro:patient-notification:sms-1",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(captured["path"], "/api/v1/notifications/send")
        self.assertEqual(captured["payload"]["channel_type"], "sms")
        self.assertEqual(
            captured["payload"]["content"],
            {
                "to_number": "+2348012345678",
                "body": "Your prescription is ready.",
            },
        )
        self.assertNotIn("subject", captured["payload"]["content"])

    def test_patient_notification_channels_are_explicit_and_deduplicated(self):
        from app.services.patient_notification_service import PatientNotificationService

        os.environ["HISPRO_PATIENT_NOTIFICATION_CHANNELS"] = " portal, sms, email, SMS, invalid "
        self.assertEqual(
            PatientNotificationService.configured_channels(),
            ["PORTAL", "SMS", "EMAIL"],
        )
