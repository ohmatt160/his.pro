from __future__ import annotations

import hashlib
import json
import re

from fastapi import HTTPException


IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{16,200}$")


class IdempotencyConflictError(ValueError):
    pass


def require_idempotency_key(value: str | None) -> str:
    if not value or not IDEMPOTENCY_KEY_PATTERN.fullmatch(value):
        raise HTTPException(
            status_code=400,
            detail="A valid Idempotency-Key header is required",
        )
    return value


def idempotency_payload_hash(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def verify_idempotent_replay(existing, payload_hash: str):
    if existing.idempotency_payload_hash != payload_hash:
        raise IdempotencyConflictError(
            "Idempotency key was already used with a different request"
        )
    return existing
