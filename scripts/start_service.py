"""Start HIS.Pro in web-only or explicit single-container mode."""

from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import sys
import time


ROOT_DIR = Path(__file__).resolve().parents[1]
_processes: list[subprocess.Popen] = []
_shutdown_requested = False


def _is_true(name: str) -> bool:
    return os.getenv(name, "").strip().lower() == "true"


def _gunicorn_command() -> list[str]:
    port = os.getenv("PORT", "7860")
    workers = os.getenv("WEB_CONCURRENCY", "2")
    return [
        os.getenv("GUNICORN_BIN", "gunicorn"),
        "--bind",
        f"0.0.0.0:{port}",
        "--workers",
        workers,
        "--worker-class",
        "uvicorn.workers.UvicornWorker",
        "--timeout",
        "120",
        "--graceful-timeout",
        "30",
        "--max-requests",
        "2000",
        "--max-requests-jitter",
        "200",
        "--access-logfile",
        "-",
        "--error-logfile",
        "-",
        "app.main:app",
    ]


def _run_migrations() -> None:
    print("[STARTUP] Applying database migrations", flush=True)
    subprocess.run(
        [sys.executable, "scripts/migrate.py"],
        cwd=ROOT_DIR,
        check=True,
    )


def _start_process(command: list[str], label: str) -> subprocess.Popen:
    print(f"[STARTUP] Starting {label}", flush=True)
    process = subprocess.Popen(command, cwd=ROOT_DIR)
    _processes.append(process)
    return process


def _stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def _request_shutdown(signum, _frame) -> None:
    global _shutdown_requested
    _shutdown_requested = True
    for process in list(_processes):
        if process.poll() is None:
            process.send_signal(signum)


def main() -> int:
    global _shutdown_requested
    _shutdown_requested = False
    _processes.clear()

    signal.signal(signal.SIGTERM, _request_shutdown)
    signal.signal(signal.SIGINT, _request_shutdown)

    if _is_true("RUN_MIGRATIONS_ON_START"):
        _run_migrations()

    worker = None
    if _is_true("BUNDLED_BACKGROUND_WORKER"):
        worker = _start_process(
            [sys.executable, "scripts/process_background_jobs.py"],
            "background worker",
        )

    web = _start_process(_gunicorn_command(), "Gunicorn")
    try:
        while True:
            if _shutdown_requested:
                return 0

            web_code = web.poll()
            if web_code is not None:
                return web_code

            if worker is not None:
                worker_code = worker.poll()
                if worker_code is not None:
                    print(
                        f"[ERROR] Background worker exited with code {worker_code}",
                        flush=True,
                    )
                    return worker_code or 1

            time.sleep(0.5)
    finally:
        for process in reversed(_processes):
            _stop_process(process)


if __name__ == "__main__":
    raise SystemExit(main())
