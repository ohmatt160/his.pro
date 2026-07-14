import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


class OhmattOSClient:
    """Best-effort client for platform services provided by OhmattOS.

    HIS Pro must remain operational if OhmattOS is disabled or temporarily
    unavailable, so every method returns a compact result and never raises.
    """

    def __init__(self):
        self.base_url = (os.getenv("OHMATTOS_URL") or "").rstrip("/")
        self.api_key = os.getenv("OHMATTOS_API_KEY") or ""
        self.app_id = os.getenv("OHMATTOS_APP_ID") or os.getenv("OHMATTOS_HISPRO_APP_ID") or ""
        self.timeout = float(os.getenv("OHMATTOS_TIMEOUT_SECONDS", "2"))

    @property
    def enabled(self) -> bool:
        return os.getenv("OHMATTOS_ENABLED", "").lower() == "true" and bool(self.base_url and self.api_key)

    def feature_enabled(self, feature: str) -> bool:
        return self.enabled and os.getenv(f"OHMATTOS_{feature.upper()}_ENABLED", "").lower() == "true"

    def submit_job(self, job_type: str, payload: dict[str, Any], priority: int = 5, max_attempts: int = 3) -> dict[str, Any]:
        return self._post("/api/v1/jobs/submit", {
            "job_type": job_type,
            "payload": payload,
            "priority": priority,
            "max_attempts": max_attempts,
        })

    def send_notification(
        self,
        *,
        user_id: str,
        channel_type: str,
        recipient: str,
        subject: str,
        body: str,
        template_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not self.app_id:
            return {"ok": False, "error": "OHMATTOS_APP_ID is not configured"}

        channel = channel_type.strip().lower()
        if channel not in {"email", "sms"}:
            return {"ok": False, "error": "Unsupported OhmattOS notification channel"}

        recipient = recipient.strip()
        body = body.strip()
        if not recipient:
            return {"ok": False, "error": "Notification recipient is required"}
        if not body:
            return {"ok": False, "error": "Notification body is required"}
        if idempotency_key and len(idempotency_key) > 200:
            return {"ok": False, "error": "Notification idempotency key is too long"}

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

        payload = {
            "app_id": self.app_id,
            "user_id": str(user_id),
            "channel_type": channel,
            "template_id": template_id,
            "content": content,
            "idempotency_key": idempotency_key,
        }
        return self._post("/api/v1/notifications/send", payload)

    def track_event(self, event_name: str, properties: dict[str, Any] | None = None, user_id: str | None = None) -> dict[str, Any]:
        if not self.app_id:
            return {"ok": False, "error": "OHMATTOS_APP_ID is not configured"}
        return self._post("/api/v1/analytics/event", {
            "app_id": self.app_id,
            "event_name": event_name,
            "user_id": str(user_id) if user_id else None,
            "properties": properties or {},
        })

    def report_error(
        self,
        *,
        message: str,
        severity: str = "error",
        context: dict[str, Any] | None = None,
        request_id: str | None = None,
        user_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        return self._post("/api/v1/logs/error", {
            "app_id": self.app_id or None,
            "severity": severity,
            "message": message[:500],
            "stack_trace": None,
            "context": context or {},
            "request_id": request_id,
            "user_id": str(user_id) if user_id else None,
            "ip_address": ip_address,
            "user_agent": user_agent,
        })

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            return {"ok": False, "error": "OhmattOS disabled"}
        url = f"{self.base_url}{path}"
        body = json.dumps(payload, default=str).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-API-Key": self.api_key,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                parsed = json.loads(raw) if raw else {}
                data = parsed.get("data") if isinstance(parsed, dict) else parsed
                return {"ok": 200 <= response.status < 300, "status": response.status, "data": data}
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            logger.warning("OhmattOS request failed status=%s path=%s body=%s", exc.code, path, error_body[:500])
            return {"ok": False, "status": exc.code, "error": "OhmattOS request failed"}
        except Exception as exc:
            logger.warning("OhmattOS unavailable for %s: %s", path, exc)
            return {"ok": False, "error": "OhmattOS unavailable"}


ohmattos_client = OhmattOSClient()
