"""Run durable HIS Pro background jobs in a dedicated worker process."""

from __future__ import annotations

import argparse
import os
import socket
import time
import uuid

import redis

from app.services.background_jobs import background_jobs


def _heartbeat(client, worker_id: str) -> None:
    if client is not None:
        client.set("hispro:worker:background_jobs", worker_id, ex=30)


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

    try:
        while True:
            _heartbeat(heartbeat_client, worker_id)
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
