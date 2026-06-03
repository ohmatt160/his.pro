from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.extensions import db_session
from app.middleware.jwt import verify_token
from app.models.facility import Facility
from app.models.user import User


MODULE_ROUTE_PREFIXES = {
    "/api/v1/patients": "reception",
    "/api/v1/appointments": "reception",
    "/api/v1/queue": "reception",
    "/api/v1/emr": "records",
    "/api/v1/consultations": "consultations",
    "/api/v1/wards": "nursing",
    "/api/v1/laboratory": "lab",
    "/api/v1/pharmacy": "pharmacy",
    "/api/v1/billing": "billing",
    "/api/v1/radiology": "radiology",
    "/api/v1/inventory": "inventory",
    "/api/v1/suppliers": "inventory",
    "/api/v1/reports": "reports",
    "/api/v1/patient-notifications": "reception",
    "/api/v1/order-workflow": "consultations",
}

MODULE_ROLE_ACCESS = {
    "reception": {"ADMIN", "RECEPTIONIST", "DOCTOR", "NURSE"},
    "records": {"ADMIN", "DOCTOR", "NURSE"},
    "consultations": {"ADMIN", "DOCTOR", "NURSE"},
    "nursing": {"ADMIN", "DOCTOR", "NURSE"},
    "lab": {"ADMIN", "DOCTOR", "LAB_TECH"},
    "pharmacy": {"ADMIN", "DOCTOR", "PHARMACIST"},
    "billing": {"ADMIN", "RECEPTIONIST"},
    "radiology": {"ADMIN", "DOCTOR"},
    "inventory": {"ADMIN", "PHARMACIST"},
    "reports": {"ADMIN", "DOCTOR", "NURSE", "RECEPTIONIST", "PHARMACIST", "LAB_TECH"},
}


def normalize_stored_modules(modules: list[str] | None) -> set[str]:
    normalized = set()
    for raw_module in modules or []:
        module = str(raw_module).strip().lower()
        normalized.add(Facility.MODULE_ALIASES.get(module, module))
    return normalized


class ModuleAccessMiddleware(BaseHTTPMiddleware):
    """Block API access to disabled tenant modules and wrong-role modules."""

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        required_module = next(
            (
                module
                for prefix, module in MODULE_ROUTE_PREFIXES.items()
                if request.url.path.startswith(prefix)
            ),
            None,
        )
        if not required_module:
            return await call_next(request)

        token = None
        authorization = request.headers.get("Authorization")
        if authorization:
            try:
                scheme, value = authorization.split()
                if scheme.lower() == "bearer":
                    token = value
            except ValueError:
                token = None
        token = token or request.cookies.get("hispro_access_token")
        if not token:
            return await call_next(request)

        try:
            payload = verify_token(token)
        except Exception:
            return await call_next(request)

        user = (
            db_session.query(User)
            .filter(User.id == payload.get("sub"), User.is_active == True)
            .first()
        )
        if not user or not user.facility_slug:
            return await call_next(request)

        facility = (
            db_session.query(Facility)
            .filter(Facility.slug == user.facility_slug, Facility.is_active == True)
            .first()
        )
        if not facility:
            return await call_next(request)

        if required_module not in normalize_stored_modules(facility.modules):
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "This module is not enabled for this facility."
                },
            )

        allowed_roles = MODULE_ROLE_ACCESS.get(required_module, {"ADMIN"})
        if user.role not in allowed_roles:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Your role cannot access this module."
                },
            )

        return await call_next(request)
