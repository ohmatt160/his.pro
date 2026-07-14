import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.metrics_service import metrics_service


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        started_at = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        route = request.url.path
        metrics_service.increment("http_requests_total")
        metrics_service.increment(f"http_status_{response.status_code // 100}xx_total")
        metrics_service.observe("http_request_duration_ms", elapsed_ms)
        if route.startswith("/api/v1/realtime"):
            metrics_service.increment("realtime_http_requests_total")
        return response
