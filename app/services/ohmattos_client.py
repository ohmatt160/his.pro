from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urljoin, urlparse

import httpx
import jwt

logger = logging.getLogger(__name__)

CLIENT_ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
ALLOWED_SIGNING_ALGORITHMS = frozenset({"RS256"})
ALLOWED_SCOPES = frozenset(
    {
        "notifications:send",
        "jobs:submit",
        "analytics:write",
        "logs:write",
    }
)
CLIENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{3,128}$")
KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{1,128}$")
IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._~:/-]{0,199}$")


class OhmattOSConfigurationError(RuntimeError):
    """Raised when an enabled OhmattOS integration is unsafe or incomplete."""


class OhmattOSAuthenticationError(RuntimeError):
    """Raised when a tenant-scoped access token cannot be obtained safely."""


@dataclass(frozen=True)
class _AccessToken:
    value: str
    expires_at: float


class OhmattOSClient:
    """Tenant-scoped machine client for optional OhmattOS platform services.

    The client assertion authenticates the HIS Pro workload. OhmattOS remains
    responsible for authorizing the requested hospital UUID and scopes before
    issuing a short-lived access token.
    """

    def __init__(
        self,
        *,
        environ: Mapping[str, str] | None = None,
        http_client: httpx.Client | None = None,
        clock=time.time,
    ):
        self._environ = environ if environ is not None else os.environ
        self._provided_http_client = http_client
        self._http_client: httpx.Client | None = http_client
        self._http_client_pid = os.getpid() if http_client else None
        self._clock = clock
        self._client_lock = threading.Lock()
        self._cache_lock = threading.Lock()
        self._refresh_locks = tuple(threading.Lock() for _ in range(64))
        self._token_cache: OrderedDict[tuple[str, str], _AccessToken] = OrderedDict()
        self._private_key: bytes | None = None
        self._private_key_pid: int | None = None

        self.base_url = self._get("OHMATTOS_URL").rstrip("/")
        self.token_url = self._get("OHMATTOS_TOKEN_URL") or (
            f"{self.base_url}/api/v1/auth/token" if self.base_url else ""
        )
        self.client_id = self._get("OHMATTOS_CLIENT_ID")
        self.private_key_file = self._get("OHMATTOS_CLIENT_PRIVATE_KEY_FILE")
        self.private_key_id = self._get("OHMATTOS_CLIENT_KEY_ID")
        self.signing_algorithm = self._get("OHMATTOS_CLIENT_SIGNING_ALG", "RS256").upper()
        self.token_audience = self._get("OHMATTOS_TOKEN_AUDIENCE") or self.token_url
        self.api_audience = self._get("OHMATTOS_API_AUDIENCE", "ohmattos-api")
        self.timeout_seconds = self._float_setting("OHMATTOS_TIMEOUT_SECONDS", 5.0, 0.1, 30.0)
        self.max_token_ttl_seconds = self._int_setting(
            "OHMATTOS_MAX_TOKEN_TTL_SECONDS", 300, 60, 300
        )
        self.token_cache_size = self._int_setting(
            "OHMATTOS_TOKEN_CACHE_SIZE", 2048, 16, 100_000
        )
        self.token_refresh_skew_seconds = self._int_setting(
            "OHMATTOS_TOKEN_REFRESH_SKEW_SECONDS", 30, 5, 120
        )

    def _get(self, key: str, default: str = "") -> str:
        value = self._environ.get(key, default)
        return str(value).strip() if value is not None else default

    def _float_setting(self, key: str, default: float, minimum: float, maximum: float) -> float:
        raw = self._get(key)
        try:
            value = float(raw) if raw else default
        except ValueError as exc:
            raise OhmattOSConfigurationError(f"{key} must be numeric") from exc
        if not minimum <= value <= maximum:
            raise OhmattOSConfigurationError(
                f"{key} must be between {minimum} and {maximum}"
            )
        return value

    def _int_setting(self, key: str, default: int, minimum: int, maximum: int) -> int:
        raw = self._get(key)
        try:
            value = int(raw) if raw else default
        except ValueError as exc:
            raise OhmattOSConfigurationError(f"{key} must be an integer") from exc
        if not minimum <= value <= maximum:
            raise OhmattOSConfigurationError(
                f"{key} must be between {minimum} and {maximum}"
            )
        return value

    @property
    def enabled(self) -> bool:
        if self._get("OHMATTOS_ENABLED").lower() != "true":
            return False
        try:
            self.validate_configuration(production=False)
        except OhmattOSConfigurationError:
            return False
        return True

    def feature_enabled(self, feature: str) -> bool:
        return (
            self.enabled
            and self._get(f"OHMATTOS_{feature.upper()}_ENABLED").lower() == "true"
        )

    def validate_configuration(self, *, production: bool) -> None:
        if self._get("OHMATTOS_ENABLED").lower() != "true":
            return

        required = {
            "OHMATTOS_URL": self.base_url,
            "OHMATTOS_TOKEN_URL": self.token_url,
            "OHMATTOS_CLIENT_ID": self.client_id,
            "OHMATTOS_CLIENT_PRIVATE_KEY_FILE": self.private_key_file,
            "OHMATTOS_CLIENT_KEY_ID": self.private_key_id,
            "OHMATTOS_TOKEN_AUDIENCE": self.token_audience,
            "OHMATTOS_API_AUDIENCE": self.api_audience,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise OhmattOSConfigurationError(
                f"enabled OhmattOS integration is missing {', '.join(missing)}"
            )

        if not CLIENT_ID_PATTERN.fullmatch(self.client_id):
            raise OhmattOSConfigurationError("OHMATTOS_CLIENT_ID has an invalid format")
        if not KEY_ID_PATTERN.fullmatch(self.private_key_id):
            raise OhmattOSConfigurationError("OHMATTOS_CLIENT_KEY_ID has an invalid format")
        if self.signing_algorithm not in ALLOWED_SIGNING_ALGORITHMS:
            raise OhmattOSConfigurationError(
                "OHMATTOS_CLIENT_SIGNING_ALG must use an approved asymmetric algorithm"
            )

        base = self._validated_url(self.base_url, "OHMATTOS_URL")
        token = self._validated_url(self.token_url, "OHMATTOS_TOKEN_URL")
        if self._origin(base) != self._origin(token):
            raise OhmattOSConfigurationError(
                "OHMATTOS_TOKEN_URL must use the same origin as OHMATTOS_URL"
            )
        if production and (base.scheme != "https" or token.scheme != "https"):
            raise OhmattOSConfigurationError("OhmattOS URLs must use HTTPS in production")
        if not production and base.scheme == "http" and base.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise OhmattOSConfigurationError(
                "plain HTTP is permitted only for a local development OhmattOS instance"
            )

        key_path = Path(self.private_key_file)
        if not key_path.is_file():
            raise OhmattOSConfigurationError(
                "OHMATTOS_CLIENT_PRIVATE_KEY_FILE does not reference a readable file"
            )
        if key_path.stat().st_size > 64 * 1024:
            raise OhmattOSConfigurationError("OhmattOS private key file is unexpectedly large")

        cert_file = self._get("OHMATTOS_MTLS_CERT_FILE")
        cert_key_file = self._get("OHMATTOS_MTLS_KEY_FILE")
        if bool(cert_file) != bool(cert_key_file):
            raise OhmattOSConfigurationError(
                "OHMATTOS_MTLS_CERT_FILE and OHMATTOS_MTLS_KEY_FILE must be set together"
            )
        for name, value in (
            ("OHMATTOS_MTLS_CERT_FILE", cert_file),
            ("OHMATTOS_MTLS_KEY_FILE", cert_key_file),
            ("OHMATTOS_CA_BUNDLE", self._get("OHMATTOS_CA_BUNDLE")),
        ):
            if value and not Path(value).is_file():
                raise OhmattOSConfigurationError(f"{name} does not reference a readable file")

        if production and self._get("OHMATTOS_API_KEY"):
            raise OhmattOSConfigurationError(
                "legacy OHMATTOS_API_KEY must be removed when asymmetric authentication is enabled"
            )

    @staticmethod
    def _validated_url(value: str, setting: str):
        parsed = urlparse(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise OhmattOSConfigurationError(f"{setting} is not a safe HTTP(S) URL")
        return parsed

    @staticmethod
    def _origin(parsed) -> tuple[str, str, int | None]:
        return parsed.scheme, parsed.hostname or "", parsed.port

    def submit_job(
        self,
        *,
        tenant_id: str,
        job_type: str,
        payload: dict[str, Any],
        priority: int = 5,
        max_attempts: int = 3,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if idempotency_key is not None and (
            not isinstance(idempotency_key, str)
            or not IDEMPOTENCY_KEY_PATTERN.fullmatch(idempotency_key)
        ):
            return {"ok": False, "error": "Job idempotency key is invalid"}
        return self._post(
            "/api/v1/jobs/submit",
            {
                "job_type": job_type,
                "payload": payload,
                "priority": priority,
                "max_attempts": max_attempts,
                "idempotency_key": idempotency_key,
            },
            tenant_id=tenant_id,
            scopes=("jobs:submit",),
            idempotency_key=idempotency_key,
        )

    def send_notification(
        self,
        *,
        tenant_id: str,
        user_id: str,
        channel_type: str,
        recipient: str,
        subject: str,
        body: str,
        template_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        channel = channel_type.strip().lower()
        if channel not in {"email", "sms"}:
            return {"ok": False, "error": "Unsupported OhmattOS notification channel"}

        recipient = recipient.strip()
        body = body.strip()
        if not recipient:
            return {"ok": False, "error": "Notification recipient is required"}
        if not body:
            return {"ok": False, "error": "Notification body is required"}
        if idempotency_key is not None and (
            not isinstance(idempotency_key, str)
            or not IDEMPOTENCY_KEY_PATTERN.fullmatch(idempotency_key)
        ):
            return {"ok": False, "error": "Notification idempotency key is invalid"}

        if channel == "email":
            content = {
                "to": recipient,
                "subject": subject.strip() or "HIS Pro notification",
                "body": body,
            }
        else:
            content = {
                "to_number": recipient,
                "body": body,
            }

        return self._post(
            "/api/v1/notifications/send",
            {
                "user_id": str(user_id),
                "channel_type": channel,
                "template_id": template_id,
                "content": content,
                "idempotency_key": idempotency_key,
            },
            tenant_id=tenant_id,
            scopes=("notifications:send",),
            idempotency_key=idempotency_key,
        )

    def track_event(
        self,
        *,
        tenant_id: str,
        event_name: str,
        properties: dict[str, Any] | None = None,
        user_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if idempotency_key is not None and (
            not isinstance(idempotency_key, str)
            or not IDEMPOTENCY_KEY_PATTERN.fullmatch(idempotency_key)
        ):
            return {"ok": False, "error": "Analytics idempotency key is invalid"}
        return self._post(
            "/api/v1/analytics/event",
            {
                "event_name": event_name,
                "user_id": str(user_id) if user_id else None,
                "properties": properties or {},
                "idempotency_key": idempotency_key,
            },
            tenant_id=tenant_id,
            scopes=("analytics:write",),
            idempotency_key=idempotency_key,
        )

    def report_error(
        self,
        *,
        tenant_id: str,
        message: str,
        severity: str = "error",
        context: dict[str, Any] | None = None,
        request_id: str | None = None,
        user_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if idempotency_key is not None and (
            not isinstance(idempotency_key, str)
            or not IDEMPOTENCY_KEY_PATTERN.fullmatch(idempotency_key)
        ):
            return {"ok": False, "error": "Log idempotency key is invalid"}
        return self._post(
            "/api/v1/logs/error",
            {
                "severity": severity,
                "message": message[:500],
                "stack_trace": None,
                "context": context or {},
                "request_id": request_id,
                "user_id": str(user_id) if user_id else None,
                "ip_address": None,
                "user_agent": None,
                "idempotency_key": idempotency_key,
            },
            tenant_id=tenant_id,
            scopes=("logs:write",),
            idempotency_key=idempotency_key,
        )

    def _post(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        tenant_id: str,
        scopes: tuple[str, ...],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if self._get("OHMATTOS_ENABLED").lower() != "true":
            return {"ok": False, "error": "OhmattOS disabled", "retryable": False}
        try:
            self.validate_configuration(production=self._is_production())
            canonical_tenant_id = self._canonical_tenant_id(tenant_id)
            normalized_scopes = self._normalize_scopes(scopes)
            access_token = self._get_access_token(canonical_tenant_id, normalized_scopes)
        except (OhmattOSConfigurationError, OhmattOSAuthenticationError, ValueError) as exc:
            logger.warning("OhmattOS request was not authorized: %s", exc)
            return {
                "ok": False,
                "error": "OhmattOS authentication unavailable",
                "retryable": True,
            }

        request_id = str(uuid.uuid4())
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Request-ID": request_id,
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        response = self._send_post(path, payload, headers)
        if response is not None and response.status_code == 401:
            self._invalidate_token(canonical_tenant_id, normalized_scopes)
            try:
                headers["Authorization"] = (
                    f"Bearer {self._get_access_token(canonical_tenant_id, normalized_scopes)}"
                )
            except OhmattOSAuthenticationError:
                return {
                    "ok": False,
                    "status": 401,
                    "error": "OhmattOS authentication unavailable",
                    "retryable": True,
                }
            response = self._send_post(path, payload, headers)

        if response is None:
            return {"ok": False, "error": "OhmattOS unavailable", "retryable": True}

        if len(response.content) > 1024 * 1024:
            logger.warning(
                "OhmattOS response exceeded the safe size limit path=%s request_id=%s",
                path,
                request_id,
            )
            return {
                "ok": False,
                "status": response.status_code,
                "error": "OhmattOS returned an invalid response",
                "retryable": False,
            }

        parsed: Any = {}
        if response.content:
            try:
                parsed = response.json()
            except (json.JSONDecodeError, ValueError):
                parsed = {}
        data = parsed.get("data") if isinstance(parsed, dict) else parsed
        if 200 <= response.status_code < 300:
            return {
                "ok": True,
                "status": response.status_code,
                "data": data if data is not None else {},
            }

        logger.warning(
            "OhmattOS request failed status=%s path=%s request_id=%s",
            response.status_code,
            path,
            request_id,
        )
        return {
            "ok": False,
            "status": response.status_code,
            "error": "OhmattOS request failed",
            "retryable": response.status_code in {408, 425, 429}
            or response.status_code >= 500,
        }

    def _send_post(
        self, path: str, payload: dict[str, Any], headers: dict[str, str]
    ) -> httpx.Response | None:
        url = urljoin(f"{self.base_url}/", path.lstrip("/"))
        if self._origin(urlparse(url)) != self._origin(urlparse(self.base_url)):
            logger.error("Blocked an OhmattOS request that changed origin")
            return None
        try:
            return self._get_http_client().post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            logger.warning("OhmattOS unavailable for %s: %s", path, exc.__class__.__name__)
            return None

    def _get_access_token(self, tenant_id: str, scopes: tuple[str, ...]) -> str:
        cache_key = (tenant_id, " ".join(scopes))
        cached = self._cached_token(cache_key)
        if cached:
            return cached

        refresh_lock = self._refresh_locks[hash(cache_key) % len(self._refresh_locks)]
        with refresh_lock:
            cached = self._cached_token(cache_key)
            if cached:
                return cached
            token = self._request_access_token(tenant_id, scopes)
            with self._cache_lock:
                self._token_cache[cache_key] = token
                self._token_cache.move_to_end(cache_key)
                while len(self._token_cache) > self.token_cache_size:
                    self._token_cache.popitem(last=False)
            return token.value

    def _cached_token(self, cache_key: tuple[str, str]) -> str | None:
        now = self._clock()
        with self._cache_lock:
            token = self._token_cache.get(cache_key)
            if token and token.expires_at - self.token_refresh_skew_seconds > now:
                self._token_cache.move_to_end(cache_key)
                return token.value
            if token:
                self._token_cache.pop(cache_key, None)
        return None

    def _invalidate_token(self, tenant_id: str, scopes: tuple[str, ...]) -> None:
        with self._cache_lock:
            self._token_cache.pop((tenant_id, " ".join(scopes)), None)

    def _request_access_token(
        self, tenant_id: str, scopes: tuple[str, ...]
    ) -> _AccessToken:
        assertion = self._create_client_assertion()
        form = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_assertion_type": CLIENT_ASSERTION_TYPE,
            "client_assertion": assertion,
            "tenant_id": tenant_id,
            "scope": " ".join(scopes),
            "audience": self.api_audience,
        }
        try:
            response = self._get_http_client().post(
                self.token_url,
                data=form,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
        except httpx.HTTPError as exc:
            raise OhmattOSAuthenticationError(
                f"token endpoint unavailable ({exc.__class__.__name__})"
            ) from exc

        if response.status_code != 200 or len(response.content) > 64 * 1024:
            raise OhmattOSAuthenticationError(
                f"token endpoint rejected the client ({response.status_code})"
            )
        try:
            parsed = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise OhmattOSAuthenticationError("token endpoint returned invalid JSON") from exc
        data = parsed.get("data") if isinstance(parsed, dict) and "data" in parsed else parsed
        if not isinstance(data, dict):
            raise OhmattOSAuthenticationError("token endpoint response has an invalid shape")

        access_token = data.get("access_token")
        token_type = str(data.get("token_type", "")).lower()
        try:
            expires_in = int(data.get("expires_in", 0))
        except (TypeError, ValueError) as exc:
            raise OhmattOSAuthenticationError("token expiry is invalid") from exc
        returned_tenant_id = data.get("external_tenant_id") or data.get("tenant_id")
        returned_scopes = tuple(
            sorted(set(str(data.get("scope", "")).split()))
        )
        returned_audience = data.get("audience")

        if (
            not isinstance(access_token, str)
            or not access_token
            or len(access_token) > 16 * 1024
        ):
            raise OhmattOSAuthenticationError("token endpoint omitted access_token")
        if token_type != "bearer":
            raise OhmattOSAuthenticationError("token endpoint returned an unsupported token type")
        if not 1 <= expires_in <= self.max_token_ttl_seconds:
            raise OhmattOSAuthenticationError("token endpoint returned an unsafe token lifetime")
        if str(returned_tenant_id) != tenant_id:
            raise OhmattOSAuthenticationError("token endpoint returned the wrong tenant")
        if returned_scopes != scopes:
            raise OhmattOSAuthenticationError("token endpoint returned the wrong scopes")
        if returned_audience != self.api_audience:
            raise OhmattOSAuthenticationError("token endpoint returned the wrong audience")

        return _AccessToken(
            value=access_token,
            expires_at=self._clock() + expires_in,
        )

    def _create_client_assertion(self) -> str:
        now = int(self._clock())
        claims = {
            "iss": self.client_id,
            "sub": self.client_id,
            "aud": self.token_audience,
            "iat": now,
            "nbf": now,
            "exp": now + 60,
            "jti": str(uuid.uuid4()),
        }
        headers = {
            "alg": self.signing_algorithm,
            "kid": self.private_key_id,
            "typ": "JWT",
        }
        try:
            return jwt.encode(
                claims,
                self._load_private_key(),
                algorithm=self.signing_algorithm,
                headers=headers,
            )
        except Exception as exc:
            raise OhmattOSAuthenticationError("client assertion signing failed") from exc

    def _load_private_key(self) -> bytes:
        current_pid = os.getpid()
        if self._private_key is not None and self._private_key_pid == current_pid:
            return self._private_key
        try:
            key = Path(self.private_key_file).read_bytes()
        except OSError as exc:
            raise OhmattOSAuthenticationError("client private key is unreadable") from exc
        if not key or len(key) > 64 * 1024:
            raise OhmattOSAuthenticationError("client private key is invalid")
        self._private_key = key
        self._private_key_pid = current_pid
        return key

    def _get_http_client(self) -> httpx.Client:
        if self._provided_http_client is not None:
            return self._provided_http_client

        current_pid = os.getpid()
        if self._http_client is not None and self._http_client_pid == current_pid:
            return self._http_client

        with self._client_lock:
            if self._http_client is not None and self._http_client_pid == current_pid:
                return self._http_client
            if self._http_client is not None:
                self._http_client.close()

            cert_file = self._get("OHMATTOS_MTLS_CERT_FILE")
            cert_key_file = self._get("OHMATTOS_MTLS_KEY_FILE")
            cert = (cert_file, cert_key_file) if cert_file and cert_key_file else None
            verify: bool | str = self._get("OHMATTOS_CA_BUNDLE") or True
            timeout = httpx.Timeout(
                timeout=self.timeout_seconds,
                connect=min(self.timeout_seconds, 5.0),
                pool=min(self.timeout_seconds, 2.0),
            )
            self._http_client = httpx.Client(
                timeout=timeout,
                verify=verify,
                cert=cert,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                follow_redirects=False,
                trust_env=self._get("OHMATTOS_TRUST_ENV_PROXY").lower() == "true",
            )
            self._http_client_pid = current_pid
            return self._http_client

    @staticmethod
    def _canonical_tenant_id(value: str) -> str:
        try:
            return str(uuid.UUID(str(value)))
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError("tenant_id must be an immutable UUID") from exc

    @staticmethod
    def _normalize_scopes(scopes: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(sorted({scope.strip().lower() for scope in scopes if scope.strip()}))
        if not normalized or any(scope not in ALLOWED_SCOPES for scope in normalized):
            raise ValueError("requested OhmattOS scope is not allowed")
        return normalized

    def _is_production(self) -> bool:
        return self._get("APP_ENV", self._get("FLASK_ENV", "development")).lower() in {
            "production",
            "staging",
        }

    def close(self) -> None:
        if self._provided_http_client is not None:
            return
        with self._client_lock:
            if self._http_client is not None:
                self._http_client.close()
                self._http_client = None
                self._http_client_pid = None


ohmattos_client = OhmattOSClient()
