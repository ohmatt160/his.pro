from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import uuid
from dataclasses import asdict
from datetime import timedelta

from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError

from app.extensions import SessionLocal, db_session
from app.models.background_job import BackgroundJob
from app.models.base_model import utc_now
from app.models.facility import Facility
from app.models.user import User
from app.services.data_migration_service import DataMigrationService, ParsedMigration

logger = logging.getLogger(__name__)

MAX_JOB_PAYLOAD_BYTES = 30 * 1024 * 1024
MAX_BATCH_SIZE = 20
IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._~:/-]{15,199}$")


class BackgroundJobConflictError(ValueError):
    pass


class BackgroundJobService:
    """Database-backed queue with tenant-scoped lookup and expiring leases."""

    def __init__(self, *, inline: bool | None = None):
        app_env = (os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "development").lower()
        configured = os.getenv("BACKGROUND_JOBS_INLINE")
        self.inline = (
            configured.lower() == "true"
            if configured is not None
            else app_env not in {"production", "staging"}
        ) if inline is None else inline

    def get(self, job_id: str, *, facility_id: str) -> BackgroundJob | None:
        try:
            canonical_job_id = str(uuid.UUID(str(job_id)))
            canonical_facility_id = str(uuid.UUID(str(facility_id)))
        except (TypeError, ValueError, AttributeError):
            return None
        return db_session.query(BackgroundJob).filter_by(
            id=canonical_job_id,
            facility_id=canonical_facility_id,
        ).first()

    def get_by_idempotency(
        self,
        *,
        name: str,
        facility_id: str,
        idempotency_key: str,
    ) -> BackgroundJob | None:
        canonical_facility_id = self._canonical_uuid(facility_id, "facility_id")
        return db_session.query(BackgroundJob).filter_by(
            facility_id=canonical_facility_id,
            name=name,
            idempotency_key=idempotency_key,
        ).first()

    def enqueue(
        self,
        name: str,
        payload: dict,
        *,
        facility_id: str,
        requested_by_user_id: str,
        idempotency_key: str,
        max_attempts: int = 3,
    ) -> tuple[BackgroundJob, bool]:
        canonical_facility_id = self._canonical_uuid(facility_id, "facility_id")
        canonical_user_id = self._canonical_uuid(
            requested_by_user_id,
            "requested_by_user_id",
        )
        if name not in BackgroundJob.NAMES:
            raise ValueError("Unsupported background job")
        if not IDEMPOTENCY_KEY_PATTERN.fullmatch(idempotency_key or ""):
            raise ValueError("A valid idempotency key is required")
        if not 1 <= max_attempts <= 10:
            raise ValueError("max_attempts must be between 1 and 10")
        encoded = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
        if len(encoded) > MAX_JOB_PAYLOAD_BYTES:
            raise ValueError("Background job payload is too large")

        existing = db_session.query(BackgroundJob).filter_by(
            facility_id=canonical_facility_id,
            name=name,
            idempotency_key=idempotency_key,
        ).first()
        if existing:
            if existing.payload_json != payload:
                raise BackgroundJobConflictError(
                    "Idempotency key was already used with a different migration"
                )
            return existing, False

        job = BackgroundJob(
            name=name,
            facility_id=canonical_facility_id,
            requested_by_user_id=canonical_user_id,
            idempotency_key=idempotency_key,
            payload_json=payload,
            status="QUEUED",
            attempts=0,
            max_attempts=max_attempts,
            available_at=utc_now(),
        )
        try:
            db_session.add(job)
            db_session.commit()
            db_session.refresh(job)
        except IntegrityError:
            db_session.rollback()
            existing = db_session.query(BackgroundJob).filter_by(
                facility_id=canonical_facility_id,
                name=name,
                idempotency_key=idempotency_key,
            ).first()
            if not existing:
                raise
            if existing.payload_json != payload:
                raise BackgroundJobConflictError(
                    "Idempotency key was already used with a different migration"
                )
            return existing, False

        if self.inline:
            asyncio.create_task(
                asyncio.to_thread(
                    self.run_job,
                    str(job.id),
                    worker_id=f"inline-{uuid.uuid4()}",
                )
            )
        return job, True

    def claim_batch(
        self,
        *,
        worker_id: str,
        batch_size: int = 5,
        lease_seconds: int = 900,
    ) -> list[str]:
        if not worker_id or len(worker_id) > 160:
            raise ValueError("worker_id must contain between 1 and 160 characters")
        if not 1 <= batch_size <= MAX_BATCH_SIZE:
            raise ValueError(f"batch_size must be between 1 and {MAX_BATCH_SIZE}")
        if not 60 <= lease_seconds <= 3600:
            raise ValueError("lease_seconds must be between 60 and 3600")

        session = SessionLocal()
        try:
            now = utc_now()
            stale_before = now - timedelta(seconds=lease_seconds)
            query = (
                session.query(BackgroundJob)
                .filter(
                    or_(
                        and_(
                            BackgroundJob.status.in_(("QUEUED", "RETRY")),
                            BackgroundJob.available_at <= now,
                        ),
                        and_(
                            BackgroundJob.status == "RUNNING",
                            BackgroundJob.locked_at < stale_before,
                        ),
                    )
                )
                .order_by(BackgroundJob.available_at.asc(), BackgroundJob.created_at.asc())
            )
            if session.bind and session.bind.dialect.name == "postgresql":
                query = query.with_for_update(skip_locked=True)
            jobs = query.limit(batch_size).all()
            ids = []
            for job in jobs:
                job.status = "RUNNING"
                job.locked_at = now
                job.lock_owner = worker_id
                job.updated_at = now
                ids.append(str(job.id))
            session.commit()
            return ids
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def run_available(
        self,
        *,
        worker_id: str,
        batch_size: int = 5,
        lease_seconds: int = 900,
    ) -> int:
        ids = self.claim_batch(
            worker_id=worker_id,
            batch_size=batch_size,
            lease_seconds=lease_seconds,
        )
        for job_id in ids:
            self.run_job(job_id, worker_id=worker_id, already_claimed=True)
        return len(ids)

    def run_job(
        self,
        job_id: str,
        *,
        worker_id: str,
        already_claimed: bool = False,
    ) -> BackgroundJob | None:
        if not already_claimed:
            session = SessionLocal()
            try:
                job = session.query(BackgroundJob).filter_by(id=job_id).first()
                if not job or job.status not in {"QUEUED", "RETRY"}:
                    return job
                job.status = "RUNNING"
                job.lock_owner = worker_id
                job.locked_at = utc_now()
                session.commit()
            finally:
                session.close()

        session = SessionLocal()
        try:
            job = session.query(BackgroundJob).filter_by(
                id=job_id,
                status="RUNNING",
                lock_owner=worker_id,
            ).first()
            if not job:
                return None
            result = self._execute(job, session)
            job.result_json = result or {}
            job.error = None
            job.status = "COMPLETED"
            job.attempts = int(job.attempts or 0) + 1
            job.lock_owner = None
            job.locked_at = None
            job.updated_at = utc_now()
            session.commit()
            return job
        except Exception as exc:
            session.rollback()
            logger.exception("Background job %s failed", job_id)
            failure_session = SessionLocal()
            try:
                job = failure_session.query(BackgroundJob).filter_by(id=job_id).first()
                if not job:
                    return None
                job.attempts = int(job.attempts or 0) + 1
                job.error = str(exc)[:2000]
                job.lock_owner = None
                job.locked_at = None
                job.updated_at = utc_now()
                if job.attempts < job.max_attempts:
                    job.status = "RETRY"
                    job.available_at = utc_now() + timedelta(
                        seconds=min(30 * (2 ** max(job.attempts - 1, 0)), 900)
                    )
                else:
                    job.status = "FAILED"
                failure_session.commit()
                return job
            finally:
                failure_session.close()
        finally:
            session.close()

    @staticmethod
    def migration_payload(parsed: ParsedMigration, facility_slug: str) -> dict:
        return {
            "facility_slug": facility_slug,
            "parsed": asdict(parsed),
        }

    @staticmethod
    def stats() -> dict:
        """Return aggregate queue health without exposing tenant payloads."""
        session = SessionLocal()
        try:
            rows = (
                session.query(BackgroundJob.status, func.count(BackgroundJob.id))
                .group_by(BackgroundJob.status)
                .all()
            )
            oldest = (
                session.query(BackgroundJob)
                .filter(BackgroundJob.status.in_(("QUEUED", "RETRY")))
                .order_by(BackgroundJob.available_at.asc())
                .first()
            )
            oldest_age_seconds = None
            if oldest:
                oldest_age_seconds = max(
                    0,
                    int((utc_now() - oldest.available_at).total_seconds()),
                )
            return {
                "counts": {status: count for status, count in rows},
                "oldest_available_age_seconds": oldest_age_seconds,
            }
        finally:
            session.close()

    @staticmethod
    def _execute(job: BackgroundJob, session) -> dict:
        if job.name != "data_migration_import":
            raise RuntimeError("Unsupported background job")
        payload = dict(job.payload_json or {})
        facility = session.query(Facility).filter_by(
            id=job.facility_id,
            slug=payload.get("facility_slug"),
            is_active=True,
        ).first()
        actor = session.query(User).filter_by(
            id=job.requested_by_user_id,
            facility_id=job.facility_id,
            is_active=True,
        ).first()
        if not facility or not actor:
            raise RuntimeError("Migration facility or actor no longer exists")
        parsed_payload = payload.get("parsed")
        if not isinstance(parsed_payload, dict):
            raise RuntimeError("Migration payload is invalid")
        parsed = ParsedMigration(**parsed_payload)
        return DataMigrationService.import_parsed(
            parsed,
            session,
            facility,
            actor,
            dry_run=False,
        )

    @staticmethod
    def _canonical_uuid(value: str, field_name: str) -> str:
        try:
            return str(uuid.UUID(str(value)))
        except (TypeError, ValueError, AttributeError) as exc:
            raise ValueError(f"{field_name} must be an immutable UUID") from exc


background_jobs = BackgroundJobService()
