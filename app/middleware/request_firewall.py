"""Application firewall middleware for high-confidence probes and risk patterns."""

from __future__ import annotations

import asyncio
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.services.request_risk_service import RequestRiskService, firewall_mode


EXEMPT_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/api/v1/openapi.json"}


class RequestFirewallMiddleware(BaseHTTPMiddleware):
    """Block only high-confidence probes; observe uncertain behavior first."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method == "OPTIONS" or request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        mode = firewall_mode()
        if mode == "off":
            return await call_next(request)

        try:
            assessment = await asyncio.to_thread(RequestRiskService.assess, request)
        except Exception:
            # Security telemetry must not turn a dependency outage into an API outage.
            return await call_next(request)

        request.state.firewall_assessment = assessment
        if assessment.action in {"block", "throttle"}:
            RequestRiskService.metric(assessment.action)
            await asyncio.to_thread(RequestRiskService.record_event, request, assessment)
            if mode == "enforce":
                status_code = 403 if assessment.action == "block" else 429
                detail = "Request blocked by security policy" if status_code == 403 else "Request temporarily throttled"
                return JSONResponse(
                    status_code=status_code,
                    content={"detail": detail},
                    headers={"Cache-Control": "no-store"},
                )
        elif assessment.action == "observe":
            RequestRiskService.metric("observe")
            await asyncio.to_thread(RequestRiskService.record_event, request, assessment)

        response = await call_next(request)
        try:
            after = await asyncio.to_thread(
                RequestRiskService.record_response,
                request,
                assessment,
                response.status_code,
            )
            if after.action != "allow" and after.rule_id:
                RequestRiskService.metric(after.action)
                await asyncio.to_thread(
                    RequestRiskService.record_event,
                    request,
                    after,
                    response_status=response.status_code,
                )
        except Exception:
            pass
        return response
