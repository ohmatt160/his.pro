import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.extensions import db_session
from app.services.audit_log_service import AuditLogService
from app.services.integration_outbox_service import IntegrationOutboxService
from app.services.metrics_service import metrics_service
from app.services.ohmattos_client import ohmattos_client

logger = logging.getLogger(__name__)

SENSITIVE_READ_PREFIXES = (
    "/api/v1/patients",
    "/api/v1/appointments",
    "/api/v1/consultations",
    "/api/v1/emr",
    "/api/v1/laboratory",
    "/api/v1/pharmacy",
    "/api/v1/billing",
    "/api/v1/wards",
    "/api/v1/files",
    "/api/v1/chat",
    "/api/v1/radiology",
    "/api/v1/referrals",
    "/api/v1/reports",
    "/api/v1/audit-logs",
    "/api/v1/inventory",
    "/api/v1/suppliers",
    "/api/v1/queue",
    "/api/v1/tasks",
    "/api/v1/alerts",
    "/api/v1/patient-notifications",
    "/api/v1/users",
)
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _resource_type(path: str) -> str:
    parts = [part for part in path.split("/") if part]
    if len(parts) >= 3:
        return parts[2].replace("-", "_")
    return "api"


class AuditMiddleware(BaseHTTPMiddleware):
    """Low-noise audit trail for sensitive API reads and writes."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        path = request.url.path
        should_audit = (
            (
                request.method in WRITE_METHODS
                and path.startswith("/api/v1/")
            )
            or (
                request.method == "GET"
                and path.startswith(SENSITIVE_READ_PREFIXES)
            )
        ) and response.status_code < 400
        if not should_audit:
            return response

        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            return response

        try:
            audit_log_id = getattr(request.state, "audit_log_id", None)
            audit_action = getattr(request.state, "audit_action", None)
            if not audit_log_id:
                audit_log = AuditLogService.log_action(
                    user_id=user_id,
                    action=f"{request.method}_{_resource_type(path).upper()}",
                    resource_type=_resource_type(path),
                    resource_id=request.path_params.get("patient_id")
                    or request.path_params.get("record_id")
                    or request.path_params.get("invoice_id")
                    or request.path_params.get("order_id")
                    or request.path_params.get("appointment_id")
                    or request.path_params.get("prescription_id")
                    or request.path_params.get("payment_id")
                    or request.path_params.get("conversation_id")
                    or request.path_params.get("facility_id")
                    or request.path_params.get("facility_slug")
                    or request.path_params.get("user_id"),
                    facility_slug=getattr(request.state, "facility_slug", None),
                    details={"path": path, "status_code": response.status_code},
                    request=request,
                    commit=True,
                    raise_on_error=True,
                )
                audit_log_id = str(audit_log.id)
                audit_action = str(audit_log.action)

            tenant_id = getattr(request.state, "tenant_id", None)
            if ohmattos_client.feature_enabled("analytics") and tenant_id:
                IntegrationOutboxService.enqueue(
                    facility_id=str(tenant_id),
                    event_type="analytics.track",
                    aggregate_type="audit_log",
                    aggregate_id=audit_log_id,
                    idempotency_key=f"hispro:analytics:{audit_log_id}",
                    payload={
                        "event_name": f"hispro.audit.{str(audit_action).lower()}",
                        "properties": {
                            "event_id": audit_log_id,
                            "resource_type": _resource_type(path),
                            "status_code": response.status_code,
                        },
                        "user_id": str(user_id),
                    },
                    session=db_session,
                )
                db_session.commit()
        except Exception:
            db_session.rollback()
            metrics_service.increment("audit_write_failures_total")
            logger.warning("Failed to write audit log for %s %s", request.method, path, exc_info=True)
        finally:
            db_session.remove()
        return response
