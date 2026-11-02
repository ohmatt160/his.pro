"""Signed proof that a particular migration file passed preflight validation."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any


class MigrationValidationTicketError(ValueError):
    pass


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _secret() -> bytes:
    configured = (
        os.getenv("MIGRATION_VALIDATION_SECRET")
        or os.getenv("JWT_SECRET_KEY")
        or os.getenv("SECRET_KEY")
        or "development-migration-validation-secret"
    )
    return configured.encode("utf-8")


def _lifetime_seconds() -> int:
    try:
        lifetime = int(os.getenv("MIGRATION_VALIDATION_TICKET_SECONDS", "900"))
    except ValueError as exc:
        raise MigrationValidationTicketError("Invalid migration validation lifetime") from exc
    if not 60 <= lifetime <= 3600:
        raise MigrationValidationTicketError("Migration validation lifetime must be between 60 and 3600 seconds")
    return lifetime


class MigrationValidationTicketService:
    @staticmethod
    def issue(
        *,
        facility_id: str,
        facility_slug: str,
        actor_id: str,
        source_system: str,
        import_mode: str,
        content_sha256: str,
    ) -> str:
        payload = {
            "v": 1,
            "fid": str(facility_id),
            "fslug": facility_slug,
            "sub": str(actor_id),
            "source": source_system,
            "mode": import_mode,
            "sha256": content_sha256,
            "iat": int(time.time()),
            "exp": int(time.time()) + _lifetime_seconds(),
            "jti": secrets.token_urlsafe(16),
        }
        body = _b64encode(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        signature = hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).digest()
        return f"{body}.{_b64encode(signature)}"

    @staticmethod
    def verify(
        ticket: str,
        *,
        facility_id: str,
        facility_slug: str,
        actor_id: str,
        source_system: str,
        import_mode: str,
        content_sha256: str,
    ) -> dict[str, Any]:
        try:
            body, provided_signature = ticket.split(".", 1)
            expected_signature = _b64encode(
                hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).digest()
            )
            if not hmac.compare_digest(provided_signature, expected_signature):
                raise MigrationValidationTicketError("Migration validation is invalid")
            payload = json.loads(_b64decode(body))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            if isinstance(exc, MigrationValidationTicketError):
                raise
            raise MigrationValidationTicketError("Migration validation is invalid") from exc

        expected = {
            "fid": str(facility_id),
            "fslug": facility_slug,
            "sub": str(actor_id),
            "source": source_system,
            "mode": import_mode,
            "sha256": content_sha256,
        }
        if int(payload.get("exp", 0)) < int(time.time()):
            raise MigrationValidationTicketError("Migration validation has expired")
        if any(not hmac.compare_digest(str(payload.get(key, "")), value) for key, value in expected.items()):
            raise MigrationValidationTicketError("Migration file or scope does not match validation")
        return payload
