import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.audit_log_service import AuditLogService
from app.services.ohmattos_client import ohmattos_client

logger = logging.getLogger(__name__)

SENSITIVE_PREFIXES = (
    "/api/v1/patients",
    "/api/v1/consultations",
    "/api/v1/emr",
    "/api/v1/laboratory/orders",
    "/api/v1/pharmacy/prescriptions",
    "/api/v1/billing",
    "/api/v1/wards",
    "/api/v1/files",
    "/api/v1/chat/files",
    "/api/v1/facilities",
)


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
            path.startswith(SENSITIVE_PREFIXES)
            and request.method in {"GET", "POST", "PUT", "PATCH", "DELETE"}
            and response.status_code < 400
        )
        if not should_audit:
            return response

        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            return response

        try:
            AuditLogService.log_action(
                user_id=user_id,
                action=f"{request.method}_{_resource_type(path).upper()}",
                resource_type=_resource_type(path),
                resource_id=request.path_params.get("patient_id")
                or request.path_params.get("record_id")
                or request.path_params.get("invoice_id")
                or request.path_params.get("order_id")
                or request.path_params.get("facility_slug"),
                facility_slug=getattr(request.state, "facility_slug", None),
                details={"path": path, "status_code": response.status_code},
                request=request,
            )
            if ohmattos_client.feature_enabled("analytics"):
                ohmattos_client.track_event(
                    f"hispro.{request.method.lower()}.{_resource_type(path)}",
                    properties={
                        "resource_type": _resource_type(path),
                        "status_code": response.status_code,
                        "facility_slug": getattr(request.state, "facility_slug", None),
                        "branch_id": getattr(request.state, "branch_id", None),
                    },
                    user_id=str(user_id),
                )
        except Exception:
            logger.warning("Failed to write audit log for %s %s", request.method, path, exc_info=True)
        return response
