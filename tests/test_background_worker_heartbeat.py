import os
import unittest
from unittest.mock import Mock, patch

from scripts import process_background_jobs


class BackgroundWorkerHeartbeatTests(unittest.TestCase):
    def test_default_heartbeat_is_throttled_with_safe_expiry(self):
        with patch.dict(os.environ, {}, clear=True):
            interval, ttl = process_background_jobs._heartbeat_settings()

        self.assertEqual(interval, 10.0)
        self.assertEqual(ttl, 30)

    def test_expiry_cannot_be_shorter_than_two_intervals(self):
        with patch.dict(
            os.environ,
            {
                "BACKGROUND_JOB_HEARTBEAT_SECONDS": "20",
                "BACKGROUND_JOB_HEARTBEAT_TTL_SECONDS": "10",
            },
            clear=True,
        ):
            interval, ttl = process_background_jobs._heartbeat_settings()

        self.assertEqual(interval, 20.0)
        self.assertEqual(ttl, 41)

    def test_heartbeat_uses_configured_expiry(self):
        client = Mock()

        process_background_jobs._heartbeat(
            client,
            "worker-1",
            ttl_seconds=45,
        )

        client.set.assert_called_once_with(
            "hispro:worker:background_jobs",
            "worker-1",
            ex=45,
        )


if __name__ == "__main__":
    unittest.main()
