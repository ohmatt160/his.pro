import os
import unittest
from unittest.mock import patch

from app.utils.production_config import validate_production_configuration


VALID_PRODUCTION_ENV = {
    "APP_ENV": "production",
    "JWT_SECRET_KEY": "j" * 48,
    "CSRF_SECRET_KEY": "c" * 48,
    "COOKIE_SECURE": "true",
    "ALLOWED_ORIGINS": "https://ohmatt160-his-pro-staging.hf.space",
    "DATABASE_URL": "postgresql+psycopg2://hispro:password@db/hispro",
    "ALLOW_SQLITE_IN_PRODUCTION": "false",
    "REDIS_URL": "rediss://redis.example.test:6380/0",
    "REALTIME_REDIS_REQUIRED": "true",
    "ALLOW_IN_MEMORY_COORDINATION": "false",
    "BACKGROUND_JOBS_INLINE": "false",
    "BACKGROUND_JOB_WORKER_ENABLED": "true",
    "METRICS_PUBLIC": "false",
    "METRICS_TOKEN": "m" * 48,
    "PUBLIC_SIGNUP_ENABLED": "false",
    "ONBOARDING_TOKEN": "o" * 48,
}


class ProductionConfigurationTests(unittest.TestCase):
    def test_valid_hardened_configuration_passes(self):
        with patch.dict(os.environ, VALID_PRODUCTION_ENV, clear=True):
            validate_production_configuration()

    def test_staging_startup_failures_remain_fail_closed(self):
        unsafe = {
            **VALID_PRODUCTION_ENV,
            "CSRF_SECRET_KEY": "change-me",
            "ALLOWED_ORIGINS": "http://localhost:5173",
            "REDIS_URL": "",
            "REALTIME_REDIS_REQUIRED": "false",
            "BACKGROUND_JOB_WORKER_ENABLED": "false",
            "METRICS_TOKEN": "change-me",
            "ONBOARDING_TOKEN": "change-me",
        }

        with patch.dict(os.environ, unsafe, clear=True), self.assertRaises(
            RuntimeError
        ) as caught:
            validate_production_configuration()

        message = str(caught.exception)
        self.assertIn("CSRF_SECRET_KEY", message)
        self.assertIn("ALLOWED_ORIGINS", message)
        self.assertIn("REDIS_URL", message)
        self.assertIn("REALTIME_REDIS_REQUIRED", message)
        self.assertIn("BACKGROUND_JOB_WORKER_ENABLED", message)
        self.assertIn("METRICS_TOKEN", message)
        self.assertIn("ONBOARDING_TOKEN", message)


if __name__ == "__main__":
    unittest.main()
