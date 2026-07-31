"""Dispatch tenant-scoped integration outbox rows.

Run this as a separate process from the FastAPI web workers. Multiple instances
may run concurrently; PostgreSQL row leases and remote idempotency make retries
safe.
"""

from __future__ import annotations

import logging
import os
import signal
import socket
import sys
import time
import uuid
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.models  # noqa: E402,F401
from app.services.integration_outbox_service import (  # noqa: E402
    IntegrationOutboxService,
)
from app.services.ohmattos_client import ohmattos_client  # noqa: E402


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("hispro.integration_outbox_worker")
stopping = False


def _stop(_signum, _frame) -> None:
    global stopping
    stopping = True


def _int_setting(name: str, default: int, minimum: int, maximum: int) -> int:
    value = int(os.getenv(name, str(default)))
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def main() -> None:
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    batch_size = _int_setting("INTEGRATION_OUTBOX_BATCH_SIZE", 25, 1, 100)
    lease_seconds = _int_setting("INTEGRATION_OUTBOX_LEASE_SECONDS", 120, 30, 900)
    poll_seconds = _int_setting("INTEGRATION_OUTBOX_POLL_SECONDS", 2, 1, 60)
    worker_id = (
        f"{socket.gethostname()}:{os.getpid()}:{str(uuid.uuid4()).split('-', 1)[0]}"
    )
    app_env = (os.getenv("APP_ENV") or os.getenv("FLASK_ENV", "development")).lower()
    ohmattos_client.validate_configuration(
        production=app_env in {"production", "staging"}
    )
    logger.info("Integration outbox worker started worker_id=%s", worker_id)

    consecutive_failures = 0
    try:
        while not stopping:
            try:
                summary = IntegrationOutboxService.dispatch_batch(
                    worker_id=worker_id,
                    client=ohmattos_client,
                    batch_size=batch_size,
                    lease_seconds=lease_seconds,
                )
                consecutive_failures = 0
                if summary.claimed:
                    logger.info(
                        "Outbox batch claimed=%s delivered=%s retried=%s dead=%s",
                        summary.claimed,
                        summary.delivered,
                        summary.retried,
                        summary.dead,
                    )
                    continue
                time.sleep(poll_seconds)
            except Exception:
                consecutive_failures += 1
                delay = min(poll_seconds * (2 ** min(consecutive_failures, 5)), 60)
                logger.exception("Integration outbox batch failed; retrying in %ss", delay)
                time.sleep(delay)
    finally:
        ohmattos_client.close()
        logger.info("Integration outbox worker stopped worker_id=%s", worker_id)


if __name__ == "__main__":
    main()
