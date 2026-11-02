import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.middleware import rate_limit


class RateLimitRedisTest(unittest.TestCase):
    def setUp(self):
        self.previous_url = os.environ.get("REDIS_URL")
        self.previous_client = rate_limit._redis_client_instance
        self.previous_client_url = rate_limit._redis_client_url
        rate_limit._redis_client_instance = None
        rate_limit._redis_client_url = None

    def tearDown(self):
        rate_limit._redis_client_instance = self.previous_client
        rate_limit._redis_client_url = self.previous_client_url
        if self.previous_url is None:
            os.environ.pop("REDIS_URL", None)
        else:
            os.environ["REDIS_URL"] = self.previous_url

    def test_redis_client_is_reused_for_same_url(self):
        os.environ["REDIS_URL"] = "redis://cache.example/0"
        client = MagicMock()
        with patch.object(rate_limit.redis, "from_url", return_value=client) as create:
            self.assertIs(rate_limit._redis_client(), client)
            self.assertIs(rate_limit._redis_client(), client)
        create.assert_called_once()

    def test_counter_and_expiry_use_one_atomic_redis_operation(self):
        client = MagicMock()
        client.eval.return_value = (2, 42)
        with patch.object(rate_limit, "_redis_client", return_value=client):
            count, reset_at = rate_limit.RateLimitMiddleware(None)._increment(
                "hispro:rate:POST:/login:127.0.0.1",
                rate_limit.RateLimitRule(5, 60),
            )

        self.assertEqual(count, 2)
        self.assertGreater(reset_at, 0)
        client.eval.assert_called_once_with(
            rate_limit._INCREMENT_SCRIPT,
            1,
            "hispro:rate:POST:/login:127.0.0.1",
            60,
        )


if __name__ == "__main__":
    unittest.main()
