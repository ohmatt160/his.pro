"""Encryption for short-lived, tenant-owned migration worker payloads."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


class MigrationPayloadCryptoError(ValueError):
    pass


def _fernet() -> Fernet:
    configured_key = os.getenv("MIGRATION_PAYLOAD_ENCRYPTION_KEY", "").strip()
    if configured_key:
        try:
            return Fernet(configured_key.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as exc:
            raise MigrationPayloadCryptoError("MIGRATION_PAYLOAD_ENCRYPTION_KEY is invalid") from exc

    # A separately configured Fernet key is required for production operations.
    # The derived key protects local development and prevents plaintext payloads
    # when an older deployment has not yet supplied that configuration.
    seed = (
        os.getenv("JWT_SECRET_KEY")
        or os.getenv("SECRET_KEY")
        or "development-migration-payload-secret"
    ).encode("utf-8")
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(seed).digest()))


def seal_payload(payload: dict[str, Any]) -> str:
    plaintext = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return _fernet().encrypt(plaintext).decode("ascii")


def open_payload(token: str) -> dict[str, Any]:
    try:
        value = _fernet().decrypt(token.encode("ascii"))
        parsed = json.loads(value)
    except (InvalidToken, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MigrationPayloadCryptoError("Migration payload cannot be decrypted") from exc
    if not isinstance(parsed, dict):
        raise MigrationPayloadCryptoError("Migration payload is invalid")
    return parsed
