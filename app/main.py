"""
HIS.Pro FastAPI Application
Converted from Flask/Flask-RESTx for better scalability
"""

import os
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import redis

# Import database and models
from app.models.base_model import Base
from app.extensions import engine, get_db

# Import API routers
from app.routes.auth import router as auth_router
from app.routes.patients import router as patients_router
from app.routes.appointments import router as appointments_router
from app.routes.laboratory import router as laboratory_router
from app.routes.pharmacy import router as pharmacy_router
from app.routes.billing import router as billing_router
from app.routes.consultations import router as consultations_router
from app.routes.wards import router as wards_router
from app.routes.emr import router as emr_router
from app.routes.users import router as users_router
from app.routes.password_reset import router as password_reset_router
from app.routes.patient_notifications import router as patient_notifications_router
from app.routes.facilities import router as facilities_router
from app.routes.radiology import router as radiology_router
from app.routes.inventory import router as inventory_router
from app.routes.suppliers import router as suppliers_router
from app.routes.reports import router as reports_router
from app.routes.order_workflow import router as order_workflow_router
from app.routes.queue import router as queue_router
from app.routes.alerts import router as alerts_router
from app.routes.dashboard import router as dashboard_router
from app.routes.audit_logs import router as audit_logs_router
from app.routes.files import router as files_router
from app.routes.tasks import router as tasks_router
from app.routes.staff_chat import router as staff_chat_router
from app.routes.referrals import router as referrals_router
from app.routes.public_profile import router as public_profile_router
from app.routes.realtime import router as realtime_router

# Import middleware and utilities
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.cors_force import ForceCORSHeadersMiddleware
from app.middleware.jwt import JWTMiddleware
from app.middleware.module_access import ModuleAccessMiddleware
from app.middleware.security import CSRFMiddleware, InputValidationMiddleware, SecurityHeadersMiddleware
from app.middleware.audit import AuditMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.utils.error_handlers import register_error_handlers
from app.utils.schema import ensure_database_schema_current
from app.services.email_service import EmailService
from app.services.realtime_service import realtime_broker
from app.services.metrics_service import metrics_service
from app.services.ohmattos_client import ohmattos_client
from app.services.tenant_service import backfill_facility_ids, register_tenant_hooks
from app.extensions import db_session
from app.models import UserSession

# Static paths
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
ASSETS_DIR = os.path.join(STATIC_DIR, "assets")

# Redis client global
redis_client = None
logger = logging.getLogger(__name__)




@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global redis_client

    print("[OK] Starting HIS.Pro FastAPI Application...")

    
    # Get the base directory
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    static_folder = os.path.join(base_dir, 'app', 'static')
    STATIC_FOLDER = static_folder
    
    # Production/staging schemas are prepared by scripts/migrate.py before
    # Gunicorn starts. Development keeps the additive compatibility path.
    try:
        app_env = (os.getenv("APP_ENV") or os.getenv("FLASK_ENV", "development")).lower()
        if app_env not in {"production", "staging"}:
            Base.metadata.create_all(bind=engine)
            ensure_database_schema_current(engine)
        backfill_facility_ids()
        print("[OK] Database tables initialized")
    except Exception as e:
        print(f"[WARNING] Database init failed: {e}")

    # Redis

    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        try:
            redis_client = redis.from_url(redis_url, socket_connect_timeout=5)
            redis_client.ping()
            print("[OK] Redis connection established")
        except Exception as e:
            if os.getenv("REALTIME_REDIS_REQUIRED", "").lower() == "true" and app_env == "production":
                raise RuntimeError("Redis is required for production realtime fanout") from e
            print(f"[WARNING] Redis connection failed: {e}")
            redis_client = None
    elif os.getenv("REALTIME_REDIS_REQUIRED", "").lower() == "true" and app_env == "production":
        raise RuntimeError("REDIS_URL must be set when REALTIME_REDIS_REQUIRED=true")

    # Email
    try:
        EmailService.init_app(app)
        print("[OK] Email service initialized")
    except Exception as e:
        print(f"[WARNING] Email service init failed: {e}")

    yield

    print("[INFO] Shutting down...")
    try:
        await realtime_broker.close()
    except Exception:
        logger.warning("Realtime broker shutdown failed", exc_info=True)
    if redis_client:
        redis_client.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""

    register_tenant_hooks()

    app_env = os.getenv('APP_ENV') or os.getenv('FLASK_ENV', 'development')
    is_production = app_env == 'production'

    app = FastAPI(
        title="HIS.Pro API",
        version="1.0",
        description="Health Information System API - FastAPI Version",
        docs_url=None if is_production else "/docs",
        redoc_url=None if is_production else "/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan
    )

    # CORS. Credentialed cookie auth requires exact origins; wildcard origins are
    # intentionally blocked in production.
    production_origins = [
        'https://his.pro',
        'https://www.his.pro',
        'https://his-pro.vercel.app',
        'https://his-pro-v1-0.vercel.app',
    ]
    local_origins = [
        'http://localhost:3000',
        'http://localhost:5173',
        'http://localhost:5175',
        'http://localhost:8080',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:5173',
        'http://127.0.0.1:5175',
        'http://127.0.0.1:8080',
    ]
    allowed_origins = [
        origin.strip().rstrip('/')
        for origin in os.getenv('ALLOWED_ORIGINS', '').split(',')
        if origin.strip()
    ]
    frontend_url = os.getenv('FRONTEND_URL', '').strip().rstrip('/')
    if frontend_url and frontend_url not in allowed_origins:
        allowed_origins.append(frontend_url)

    if app_env == 'production' and not allowed_origins:
        allowed_origins = production_origins.copy()
    elif not allowed_origins:
        allowed_origins = local_origins + production_origins
    if app_env == 'production' and "*" in allowed_origins:
        raise RuntimeError("Wildcard CORS origins are not allowed in production")
    allowed_origin_regex = os.getenv('ALLOWED_ORIGIN_REGEX') or None

    # DB session middleware
    @app.middleware("http")
    async def db_session_middleware(request: Request, call_next):
        try:
            response = await call_next(request)
            db_session.commit()
            return response
        except Exception as exc:
            db_session.rollback()
            if ohmattos_client.feature_enabled("logs"):
                ohmattos_client.report_error(
                    message=str(exc),
                    severity="error",
                    context={
                        "path": request.url.path,
                        "method": request.method,
                        "facility_slug": getattr(request.state, "facility_slug", None),
                        "branch_id": getattr(request.state, "branch_id", None),
                    },
                    user_id=getattr(request.state, "user_id", None),
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                )
            raise
        finally:
            db_session.remove()

    @app.middleware("http")
    async def request_timing_middleware(request: Request, call_next):
        started_at = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        response.headers["Server-Timing"] = f"app;dur={elapsed_ms:.1f}"
        slow_request_ms = float(os.getenv("SLOW_REQUEST_MS", "1000"))
        if elapsed_ms >= slow_request_ms:
            logger.warning(
                "Slow request %.1fms %s %s status=%s",
                elapsed_ms,
                request.method,
                request.url.path,
                response.status_code,
            )
        return response

    @app.get("/debug/cors", include_in_schema=False)
    async def debug_cors():
        if is_production:
            raise HTTPException(status_code=404, detail="Not found")
        return {
            "allowed_origins": allowed_origins,
            "app_env": app_env,
            "frontend_url": frontend_url,
        }

    # Add this debug endpoint temporarily
    @app.get("/debug/middleware", include_in_schema=False)
    async def debug_middleware():
        if is_production:
            raise HTTPException(status_code=404, detail="Not found")
        import app.middleware.cors_force as cf
        middlewares = [m.__class__.__name__ for m in app.user_middleware]
        return {
            "has_force_cors": hasattr(cf, 'ForceCORSHeadersMiddleware'),
            "middleware_stack": middlewares,
            "force_cors_loaded": "ForceCORSHeadersMiddleware" in str(middlewares)
        }


    # Keep CORS as the outer edge of the ASGI stack so preflight and
    # middleware-generated errors always include credentialed CORS headers.
    app.add_middleware(
        ForceCORSHeadersMiddleware,
        allowed_origins=allowed_origins,
        allowed_origin_regex=allowed_origin_regex,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=allowed_origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "Accept", "X-CSRF-Token", "X-HISPro-Authorization"],
        expose_headers=["Authorization"],
    )

    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(InputValidationMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(ModuleAccessMiddleware)
    app.add_middleware(JWTMiddleware)
    register_error_handlers(app)

    # Health check
    @app.get("/health")
    async def health_check():
        health_status = {"status": "healthy"}
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            health_status["database"] = "connected"
        except Exception:
            health_status["database"] = "error"
            health_status["status"] = "unhealthy"
        if redis_client:
            try:
                redis_client.ping()
                health_status["redis"] = "connected"
            except Exception:
                health_status["redis"] = "error"
        else:
            health_status["redis"] = "not configured"
        return health_status

    @app.get("/metrics", include_in_schema=False)
    async def metrics(request: Request):
        public = os.getenv("METRICS_PUBLIC", "").lower() == "true"
        token = os.getenv("METRICS_TOKEN", "")
        provided = request.headers.get("x-metrics-token") or request.query_params.get("token")
        if not public and (not token or provided != token):
            raise HTTPException(status_code=404, detail="Not found")
        snapshot = metrics_service.snapshot()
        snapshot["realtime"] = realtime_broker.stats()
        return snapshot

    # API routers
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(patients_router, prefix="/api/v1")
    app.include_router(appointments_router, prefix="/api/v1")
    app.include_router(laboratory_router, prefix="/api/v1")
    app.include_router(pharmacy_router, prefix="/api/v1")
    app.include_router(billing_router, prefix="/api/v1")
    app.include_router(consultations_router, prefix="/api/v1")
    app.include_router(wards_router, prefix="/api/v1")
    app.include_router(emr_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(password_reset_router, prefix="/api/v1")
    app.include_router(patient_notifications_router, prefix="/api/v1")
    app.include_router(facilities_router, prefix="/api/v1")
    app.include_router(radiology_router, prefix="/api/v1")
    app.include_router(inventory_router, prefix="/api/v1")
    app.include_router(suppliers_router, prefix="/api/v1")
    app.include_router(reports_router, prefix="/api/v1")
    app.include_router(order_workflow_router, prefix="/api/v1")
    app.include_router(queue_router, prefix="/api/v1")
    app.include_router(alerts_router, prefix="/api/v1")
    app.include_router(dashboard_router, prefix="/api/v1")
    app.include_router(audit_logs_router, prefix="/api/v1")
    app.include_router(files_router, prefix="/api/v1")
    app.include_router(tasks_router, prefix="/api/v1")
    app.include_router(staff_chat_router, prefix="/api/v1")
    app.include_router(referrals_router, prefix="/api/v1")
    app.include_router(public_profile_router, prefix="/api/v1")
    app.include_router(realtime_router, prefix="/api/v1")

    # Static mounts (assets first, then root SPA fallback)
    if os.path.isdir(ASSETS_DIR):
        app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1  # Windows fix
    )
