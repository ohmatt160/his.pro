"""Adaptive, privacy-preserving request risk scoring for the application edge."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote

import redis
from fastapi import Request

from app.extensions import SessionLocal
from app.models.security_event import SecurityEvent
from app.services.metrics_service import metrics_service
from app.utils.network import client_ip

logger = logging.getLogger(__name__)

STATE_TTL_SECONDS = 10 * 60
MAX_MEMORY_SUBJECTS = 20_000
_memory_states: dict[str, tuple[dict[str, Any], float]] = {}
_event_deduplication: dict[str, float] = {}
_redis_client = None
_redis_url = None

SCANNER_PATHS = (
    "/.env",
    "/.git",
    "/wp-admin",
    "/wp-login.php",
    "/phpmyadmin",
    "/server-status",
    "/cgi-bin",
    "/actuator",
    "/vendor/phpunit",
)
TRAVERSAL_PATTERN = re.compile(r"(?:\.\.|%2e|%2f|%5c|\\)", re.IGNORECASE)
QUERY_ATTACK_PATTERN = re.compile(
    r"(?:union(?:%20|\s)+select|select(?:%20|\s)+.+(?:from|into)|<script|javascript:|\$\{jndi:|/etc/passwd)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RiskAssessment:
    subject_hash: str
    endpoint_hash: str
    score: int
    action: str
    rule_id: str | None = None
    category: str | None = None
    normal_retry: bool = False


def _app_environment() -> str:
    return (os.getenv("APP_ENV") or os.getenv("FLASK_ENV", "development")).lower()


def _firewall_mode() -> str:
    configured = os.getenv("FIREWALL_MODE", "").lower()
    if configured in {"off", "observe", "enforce"}:
        return configured
    return "enforce" if _app_environment() in {"production", "staging"} else "observe"


def _hash(value: str) -> str:
    secret = (
        os.getenv("FIREWALL_HASH_SECRET")
        or os.getenv("CSRF_SECRET_KEY")
        or os.getenv("JWT_SECRET_KEY")
        or os.getenv("SECRET_KEY")
        or "development-firewall-hash-secret"
    ).encode("utf-8")
    return hmac.new(secret, value.encode("utf-8", errors="ignore"), hashlib.sha256).hexdigest()


def _threshold() -> int:
    try:
        value = int(os.getenv("FIREWALL_BLOCK_THRESHOLD", "15"))
    except ValueError:
        value = 15
    return min(max(value, 8), 100)


def _get_redis():
    global _redis_client, _redis_url
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        return None
    if _redis_client is None or _redis_url != redis_url:
        _redis_client = redis.from_url(
            redis_url,
            socket_connect_timeout=0.15,
            socket_timeout=0.15,
        )
        _redis_url = redis_url
    return _redis_client


class RequestRiskService:
    """Use a shared Redis ledger when present, with bounded local fallback."""

    @staticmethod
    def _state_key(subject_hash: str) -> str:
        return f"{os.getenv('FIREWALL_NAMESPACE', 'hispro')}:firewall:{subject_hash}"

    @classmethod
    def _load(cls, subject_hash: str) -> dict[str, Any]:
        now = time.time()
        try:
            client = _get_redis()
            if client:
                raw = client.get(cls._state_key(subject_hash))
                if raw:
                    return json.loads(raw)
        except (redis.RedisError, ValueError, json.JSONDecodeError):
            logger.warning("Firewall Redis ledger unavailable", exc_info=True)

        state, expires_at = _memory_states.get(subject_hash, ({}, 0))
        if expires_at <= now:
            return {}
        return dict(state)

    @classmethod
    def _store(cls, subject_hash: str, state: dict[str, Any]) -> None:
        now = time.time()
        try:
            client = _get_redis()
            if client:
                client.setex(
                    cls._state_key(subject_hash),
                    STATE_TTL_SECONDS,
                    json.dumps(state, separators=(",", ":")),
                )
                return
        except redis.RedisError:
            logger.warning("Firewall Redis ledger write failed", exc_info=True)

        if len(_memory_states) >= MAX_MEMORY_SUBJECTS:
            expired = [key for key, (_, expires_at) in _memory_states.items() if expires_at <= now]
            for key in expired[:1000]:
                _memory_states.pop(key, None)
            if len(_memory_states) >= MAX_MEMORY_SUBJECTS:
                _memory_states.pop(next(iter(_memory_states)), None)
        _memory_states[subject_hash] = (dict(state), now + STATE_TTL_SECONDS)

    @staticmethod
    def _request_identity(request: Request) -> tuple[str, str, str | None]:
        subject_hash = _hash(f"ip:{client_ip(request)}")
        endpoint_hash = _hash(f"{request.method}:{request.url.path}")
        idempotency_key = request.headers.get("idempotency-key")
        return subject_hash, endpoint_hash, _hash(f"idempotency:{idempotency_key}") if idempotency_key else None

    @staticmethod
    def _request_rule(request: Request) -> tuple[str | None, str | None, bool]:
        path = unquote(request.url.path).lower()
        query = unquote(request.url.query).lower()
        if any(fragment in path for fragment in SCANNER_PATHS):
            return "scanner-path", "scanner", True
        if TRAVERSAL_PATTERN.search(path):
            return "path-traversal", "injection", True
        if QUERY_ATTACK_PATTERN.search(query):
            return "query-injection", "injection", False
        return None, None, False

    @classmethod
    def assess(cls, request: Request) -> RiskAssessment:
        subject_hash, endpoint_hash, idempotency_hash = cls._request_identity(request)
        rule_id, category, critical = cls._request_rule(request)
        if not rule_id:
            return RiskAssessment(
                subject_hash=subject_hash,
                endpoint_hash=endpoint_hash,
                score=0,
                action="allow",
            )

        state = cls._load(subject_hash)
        now = time.time()
        last_seen = float(state.get("last_seen", now))
        previous_score = max(0, int(state.get("score", 0)) - int((now - last_seen) // 60))
        normal_retry = bool(
            idempotency_hash
            and idempotency_hash == state.get("last_idempotency_hash")
            and now - float(state.get("last_retry_at", 0)) < 120
        )
        score = previous_score
        if rule_id == "scanner-path":
            score += 25
        elif rule_id == "path-traversal":
            score += 20
        elif rule_id == "query-injection":
            score += 10

        state.update(
            {
                "score": min(score, 100),
                "last_seen": now,
                "last_idempotency_hash": idempotency_hash,
                "last_retry_at": now if idempotency_hash else state.get("last_retry_at", 0),
            }
        )
        cls._store(subject_hash, state)

        threshold = _threshold()
        if critical or score >= threshold:
            action = "block"
        elif score >= max(6, threshold * 2 // 3):
            action = "throttle"
        elif rule_id or score >= max(3, threshold // 3):
            action = "observe"
        else:
            action = "allow"
        return RiskAssessment(
            subject_hash=subject_hash,
            endpoint_hash=endpoint_hash,
            score=min(score, 100),
            action=action,
            rule_id=rule_id,
            category=category,
            normal_retry=normal_retry,
        )

    @classmethod
    def record_response(cls, request: Request, assessment: RiskAssessment, status_code: int) -> RiskAssessment:
        if assessment.normal_retry:
            return assessment
        if not assessment.rule_id and status_code not in {401, 403, 404, 405, 429}:
            return assessment
        state = cls._load(assessment.subject_hash)
        now = time.time()
        score = int(state.get("score", assessment.score))
        endpoint_hash = assessment.endpoint_hash
        rule_id = assessment.rule_id
        category = assessment.category

        if status_code in {401, 403, 404, 405}:
            recent_paths = [
                entry
                for entry in state.get("denied_paths", [])
                if now - float(entry.get("at", 0)) < 300
            ]
            new_path = not any(entry.get("path") == endpoint_hash for entry in recent_paths)
            if new_path:
                recent_paths.append({"path": endpoint_hash, "at": now})
            state["denied_paths"] = recent_paths[-12:]
            if new_path and len(recent_paths) >= 5:
                score += 6
                rule_id = rule_id or "enumeration-pattern"
                category = category or "adaptive"
        elif status_code == 429:
            score += 1

        state["score"] = min(score, 100)
        state["last_seen"] = now
        cls._store(assessment.subject_hash, state)
        threshold = _threshold()
        action = "block" if score >= threshold else "throttle" if score >= max(6, threshold * 2 // 3) else "observe" if rule_id else "allow"
        return RiskAssessment(
            subject_hash=assessment.subject_hash,
            endpoint_hash=endpoint_hash,
            score=min(score, 100),
            action=action,
            rule_id=rule_id,
            category=category,
            normal_retry=False,
        )

    @staticmethod
    def record_event(request: Request, assessment: RiskAssessment, *, response_status: int | None = None) -> None:
        if assessment.action == "allow" or not assessment.rule_id:
            return
        event_key = _hash(
            f"{assessment.subject_hash}:{assessment.rule_id}:{assessment.action}:{assessment.endpoint_hash}"
        )
        now = time.time()
        if now - _event_deduplication.get(event_key, 0) < 60:
            return
        _event_deduplication[event_key] = now
        if len(_event_deduplication) > MAX_MEMORY_SUBJECTS:
            for key, last_seen in list(_event_deduplication.items())[:1000]:
                if now - last_seen > 300:
                    _event_deduplication.pop(key, None)

        session = SessionLocal()
        try:
            session.add(
                SecurityEvent(
                    facility_id=getattr(request.state, "tenant_id", None),
                    facility_slug=getattr(request.state, "facility_slug", None),
                    subject_hash=assessment.subject_hash,
                    category=assessment.category or "adaptive",
                    rule_id=assessment.rule_id,
                    severity="high" if assessment.action == "block" else "medium",
                    action=assessment.action,
                    method=request.method,
                    endpoint_hash=assessment.endpoint_hash,
                    response_status=response_status,
                    score=assessment.score,
                    metadata_json={"normal_retry": assessment.normal_retry},
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            logger.warning("Could not persist firewall security event", exc_info=True)
        finally:
            session.close()

    @staticmethod
    def metric(action: str) -> None:
        if action == "block":
            metrics_service.increment("firewall_blocks_total")
        elif action == "throttle":
            metrics_service.increment("firewall_throttles_total")
        elif action == "observe":
            metrics_service.increment("firewall_observations_total")


def firewall_mode() -> str:
    return _firewall_mode()
