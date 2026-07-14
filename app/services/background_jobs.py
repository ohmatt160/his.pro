import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Awaitable, Callable

from app.services.ohmattos_client import ohmattos_client

logger = logging.getLogger(__name__)


@dataclass
class BackgroundJob:
    id: str
    name: str
    status: str = "queued"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z"))
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z"))
    result: dict | None = None
    error: str | None = None
    external_job_id: str | None = None


class BackgroundJobService:
    def __init__(self):
        self._jobs: dict[str, BackgroundJob] = {}
        self._semaphore = asyncio.Semaphore(2)

    def get(self, job_id: str) -> BackgroundJob | None:
        return self._jobs.get(job_id)

    def enqueue(
        self,
        name: str,
        handler: Callable[[], Awaitable[dict] | dict],
        *,
        metadata: dict | None = None,
    ) -> BackgroundJob:
        job = BackgroundJob(id=str(uuid.uuid4()), name=name)
        self._jobs[job.id] = job
        if ohmattos_client.feature_enabled("jobs"):
            asyncio.create_task(self._mirror_to_ohmattos(job, metadata or {}))
        asyncio.create_task(self._run(job, handler))
        return job

    async def _mirror_to_ohmattos(self, job: BackgroundJob, metadata: dict) -> None:
        result = await asyncio.to_thread(
            ohmattos_client.submit_job,
            f"hispro.{job.name}",
            {
                "local_job_id": job.id,
                "source": "his_pro",
                "metadata": metadata,
            },
        )
        external_id = (result.get("data") or {}).get("job_id") if result.get("ok") else None
        if external_id:
            job.external_job_id = str(external_id)

    async def _run(self, job: BackgroundJob, handler: Callable[[], Awaitable[dict] | dict]) -> None:
        async with self._semaphore:
            job.status = "running"
            job.updated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            try:
                result = handler()
                if asyncio.iscoroutine(result):
                    result = await result
                job.result = result or {}
                job.status = "completed"
            except Exception as exc:
                logger.exception("Background job %s failed", job.id)
                job.error = str(exc)
                job.status = "failed"
            finally:
                job.updated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")


background_jobs = BackgroundJobService()
