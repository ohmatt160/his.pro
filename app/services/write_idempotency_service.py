from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError

from app.extensions import db_session
from app.models.write_idempotency import WriteIdempotencyRecord
from app.utils.idempotency import (
    IdempotencyConflictError,
    idempotency_payload_hash,
    require_idempotency_key,
)


@dataclass(frozen=True)
class WriteClaim:
    record: WriteIdempotencyRecord
    replay: bool


class WriteIdempotencyService:
    """Claims an operation key before a mutation and records its resource."""

    @staticmethod
    def claim(
        *,
        facility_slug: str,
        operation: str,
        idempotency_key: str | None,
        payload: dict,
        actor_id: str | None = None,
        facility_id: str | None = None,
    ) -> WriteClaim:
        key = require_idempotency_key(idempotency_key)
        payload_hash = idempotency_payload_hash(payload)
        query = db_session.query(WriteIdempotencyRecord).filter_by(
            facility_slug=facility_slug,
            operation=operation,
            idempotency_key=key,
        )
        existing = query.first()
        if existing:
            return WriteIdempotencyService._existing_claim(
                existing,
                payload_hash,
                actor_id,
            )

        record = WriteIdempotencyRecord(
            facility_id=facility_id,
            facility_slug=facility_slug,
            actor_id=actor_id,
            operation=operation,
            idempotency_key=key,
            payload_hash=payload_hash,
            status="IN_PROGRESS",
        )
        db_session.add(record)
        try:
            # The unique index serializes identical keys across workers. The
            # surrounding business mutation is committed in the same session.
            db_session.flush()
            return WriteClaim(record=record, replay=False)
        except IntegrityError:
            db_session.rollback()
            existing = query.first()
            if not existing:
                raise
            return WriteIdempotencyService._existing_claim(
                existing,
                payload_hash,
                actor_id,
            )

    @staticmethod
    def complete(
        record: WriteIdempotencyRecord,
        *,
        resource_type: str,
        resource_id: str,
        response_status: int,
    ) -> None:
        record.status = "COMPLETED"
        record.resource_type = resource_type
        record.resource_id = str(resource_id)
        record.response_status = response_status
        db_session.add(record)

    @staticmethod
    def complete_many(
        record: WriteIdempotencyRecord,
        *,
        resource_type: str,
        resource_ids: list[str],
        response_status: int,
    ) -> None:
        normalized_ids = [str(resource_id) for resource_id in resource_ids]
        if not normalized_ids:
            raise ValueError("At least one resource is required")
        record.status = "COMPLETED"
        record.resource_type = resource_type
        record.resource_id = normalized_ids[0]
        record.resource_ids = normalized_ids
        record.response_status = response_status
        db_session.add(record)

    @staticmethod
    def _existing_claim(
        record: WriteIdempotencyRecord,
        payload_hash: str,
        actor_id: str | None,
    ) -> WriteClaim:
        if record.actor_id and actor_id and str(record.actor_id) != str(actor_id):
            raise IdempotencyConflictError(
                "Idempotency key belongs to a different user"
            )
        if record.payload_hash != payload_hash:
            raise IdempotencyConflictError(
                "Idempotency key was already used with a different request"
            )
        if record.status != "COMPLETED" or not (
            record.resource_id or record.resource_ids
        ):
            raise IdempotencyConflictError(
                "An identical request is still being processed"
            )
        return WriteClaim(record=record, replay=True)
