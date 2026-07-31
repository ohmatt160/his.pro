"""Fail-fast validation for security and scaling requirements in production."""

from __future__ import annotations

import os
import hmac


PLACEHOLDER_FRAGMENTS = {
    "replace-with",
    "change-me",
    "changeme",
    "development",
    "example",
    "secret-key",
}


def _is_true(name: str) -> bool:
    return os.getenv(name, "").strip().lower() == "true"


def _strong_secret(value: str) -> bool:
    normalized = value.strip().lower()
    return (
        len(value.strip()) >= 32
        and not any(fragment in normalized for fragment in PLACEHOLDER_FRAGMENTS)
    )


def validate_production_configuration() -> None:
    app_env = (os.getenv("APP_ENV") or os.getenv("FLASK_ENV", "development")).lower()
    if app_env not in {"production", "staging"}:
        return

    errors: list[str] = []
    jwt_secret = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY") or ""
    csrf_secret = os.getenv("CSRF_SECRET_KEY") or ""
    database_url = os.getenv("DATABASE_URL", "")
    allowed_origins = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]

    if not _strong_secret(jwt_secret):
        errors.append("JWT_SECRET_KEY must be a non-placeholder secret of at least 32 characters")
    if not _strong_secret(csrf_secret):
        errors.append("CSRF_SECRET_KEY must be a separate non-placeholder secret of at least 32 characters")
    elif jwt_secret and hmac.compare_digest(jwt_secret, csrf_secret):
        errors.append("CSRF_SECRET_KEY must not reuse JWT_SECRET_KEY")
    if not _is_true("COOKIE_SECURE"):
        errors.append("COOKIE_SECURE must be true")
    if not allowed_origins or "*" in allowed_origins:
        errors.append("ALLOWED_ORIGINS must contain explicit HTTPS origins and no wildcard")
    if any(not origin.startswith("https://") for origin in allowed_origins):
        errors.append("Every production ALLOWED_ORIGINS entry must use HTTPS")

    if not database_url:
        errors.append("DATABASE_URL is required")
    elif database_url.startswith("sqlite") and not _is_true("ALLOW_SQLITE_IN_PRODUCTION"):
        errors.append("Production requires PostgreSQL; SQLite is allowed only with explicit emergency override")

    if not os.getenv("REDIS_URL") and not _is_true("ALLOW_IN_MEMORY_COORDINATION"):
        errors.append("REDIS_URL is required for distributed rate limits, realtime fanout, and jobs")
    if not _is_true("REALTIME_REDIS_REQUIRED") and not _is_true("ALLOW_IN_MEMORY_COORDINATION"):
        errors.append("REALTIME_REDIS_REQUIRED must be true")
    if _is_true("BACKGROUND_JOBS_INLINE"):
        errors.append("BACKGROUND_JOBS_INLINE must be false in production")
    if not _is_true("BACKGROUND_JOB_WORKER_ENABLED"):
        errors.append("BACKGROUND_JOB_WORKER_ENABLED must be true")

    if not _is_true("METRICS_PUBLIC"):
        metrics_token = os.getenv("METRICS_TOKEN", "")
        if not _strong_secret(metrics_token):
            errors.append("METRICS_TOKEN must be a non-placeholder secret of at least 32 characters")

    if _is_true("PUBLIC_SIGNUP_ENABLED"):
        errors.append(
            "PUBLIC_SIGNUP_ENABLED cannot be enabled until owner email verification is enforced"
        )
    else:
        onboarding_token = os.getenv("ONBOARDING_TOKEN", "")
        if not _strong_secret(onboarding_token):
            errors.append(
                "ONBOARDING_TOKEN must be a non-placeholder secret of at least 32 characters"
            )
        elif any(
            secret and hmac.compare_digest(onboarding_token, secret)
            for secret in (jwt_secret, csrf_secret)
        ):
            errors.append("ONBOARDING_TOKEN must not reuse an application signing secret")

    if errors:
        formatted = "\n - ".join(errors)
        raise RuntimeError(f"Unsafe production configuration:\n - {formatted}")
