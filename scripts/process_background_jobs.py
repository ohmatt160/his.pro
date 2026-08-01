"""Run durable HIS Pro background jobs in a dedicated worker process."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import socket
import sys
import time
import uuid

import redis


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.background_jobs import background_jobs


def _heartbeat(client, worker_id: str, *, ttl_seconds: int) -> None:
    if client is not None:
        client.set(
            "hispro:worker:background_jobs",
            worker_id,
            ex=ttl_seconds,
        )


def _heartbeat_settings() -> tuple[float, int]:
    try:
        interval = float(os.getenv("BACKGROUND_JOB_HEARTBEAT_SECONDS", "10"))
    except ValueError:
        interval = 10.0
    interval = max(interval, 1.0)

    try:
        configured_ttl = int(os.getenv("BACKGROUND_JOB_HEARTBEAT_TTL_SECONDS", "30"))
    except ValueError:
        configured_ttl = 30
    ttl = max(configured_ttl, int(interval * 2) + 1)
    return interval, ttl


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    args = parser.parse_args()
    worker_id = (
        f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
    )
    redis_url = os.getenv("REDIS_URL")
    heartbeat_client = (
        redis.from_url(redis_url, socket_connect_timeout=5)
        if redis_url
        else None
    )
    heartbeat_interval, heartbeat_ttl = _heartbeat_settings()
    next_heartbeat_at = 0.0

    try:
        while True:
            now = time.monotonic()
            if now >= next_heartbeat_at:
                _heartbeat(
                    heartbeat_client,
                    worker_id,
                    ttl_seconds=heartbeat_ttl,
                )
                next_heartbeat_at = now + heartbeat_interval
            processed = background_jobs.run_available(
                worker_id=worker_id,
                batch_size=args.batch_size,
            )
            if args.once:
                return
            if processed == 0:
                time.sleep(max(args.poll_seconds, 0.2))
    finally:
        if heartbeat_client is not None:
            heartbeat_client.close()


if __name__ == "__main__":
    main()
