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
        result = client.send_notification(user_id="patient-1", channel_type="sms", content={"message": "Hi"})
        self.assertFalse(result["ok"])
        self.assertIn("APP_ID", result["error"])
