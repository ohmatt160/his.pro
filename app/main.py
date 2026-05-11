"""
HIS.Pro FastAPI Application
Converted from Flask/Flask-RESTx for better scalability
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import pathlib
import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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
from app.routes.emr import router as emr_router
from app.routes.users import router as users_router
from app.routes.password_reset import router as password_reset_router
from app.routes.facilities import router as facilities_router
from app.routes.radiology import router as radiology_router
from app.routes.inventory import router as inventory_router
from app.routes.queue import router as queue_router
from app.routes.alerts import router as alerts_router
from app.routes.dashboard import router as dashboard_router
from app.routes.audit_logs import router as audit_logs_router
from app.routes.files import router as files_router

# Import middleware and utilities
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.jwt import JWTMiddleware
from app.utils.error_handlers import register_error_handlers
from app.services.email_service import EmailService
from app.extensions import db_session

# Global variables
STATIC_FOLDER = None
redis_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global STATIC_FOLDER, redis_client
    
    # Startup
    print("[OK] Starting HIS.Pro FastAPI Application...")
    
    # Get the base directory
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    static_folder = os.path.join(base_dir, 'app', 'static')
    STATIC_FOLDER = static_folder
    
    # Initialize database using existing engine from extensions
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables initialized")
    
    # Initialize Redis if available
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        try:
            redis_client = redis.from_url(redis_url)
            redis_client.ping()
            print("[OK] Redis connection established")
        except Exception as e:
            print(f"[WARNING] Redis connection failed: {e}")
            redis_client = None
    else:
        redis_client = None
    
    # Initialize email service
    EmailService.init_app(app)
    print("[OK] Email service initialized")
    
    yield
    
    # Shutdown
    print("[INFO] Shutting down HIS.Pro FastAPI Application...")
    if redis_client:
        redis_client.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    
    app = FastAPI(
        title="HIS.Pro API",
        version="1.0",
        description="Health Information System API - FastAPI Version",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan
    )
    
    # Configure CORS
    allowed_origins = os.getenv('ALLOWED_ORIGINS', '').split(',') if os.getenv('ALLOWED_ORIGINS') else []

    # Default to specific origins in production, allow all in dev
    if os.getenv('FLASK_ENV') == 'production' and not allowed_origins:
        allowed_origins = ['https://his.pro', 'https://www.his.pro']
    elif not allowed_origins:
        # Development: allow localhost and common dev ports
        allowed_origins = [
            'http://localhost:3000',
            'http://localhost:5173',
            'http://localhost:8080',
            'http://127.0.0.1:3000',
            'http://127.0.0.1:5173',
            'http://127.0.0.1:8080',
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "Accept"],
        expose_headers=["Authorization"],
    )

    # Database session management middleware
    @app.middleware("http")
    async def db_session_middleware(request: Request, call_next):
        """Manage database session lifecycle per request"""
        try:
            response = await call_next(request)
            db_session.commit()
            return response
        except Exception:
            db_session.rollback()
            raise
        finally:
            db_session.remove()

    # Add custom middleware
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(JWTMiddleware)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    
    # Include API routers with /api/v1 prefix to match original API structure
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(patients_router, prefix="/api/v1")
    app.include_router(appointments_router, prefix="/api/v1")
    app.include_router(laboratory_router, prefix="/api/v1")
    app.include_router(pharmacy_router, prefix="/api/v1")
    app.include_router(billing_router, prefix="/api/v1")
    app.include_router(emr_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(password_reset_router, prefix="/api/v1")
    app.include_router(facilities_router, prefix="/api/v1")
    app.include_router(radiology_router, prefix="/api/v1")
    app.include_router(inventory_router, prefix="/api/v1")
    app.include_router(queue_router, prefix="/api/v1")
    app.include_router(alerts_router, prefix="/api/v1")
    app.include_router(dashboard_router, prefix="/api/v1")
    app.include_router(audit_logs_router, prefix="/api/v1")
    app.include_router(files_router, prefix="/api/v1")
    # All routers converted from Flask-RESTx resources
    
    # Serve index.html for root path
    @app.get("/", response_class=HTMLResponse)
    async def serve_index():
        """Serve the main SPA index.html"""
        from fastapi.responses import FileResponse
        import pathlib
        
        static_file = pathlib.Path(STATIC_FOLDER) / 'index.html'
        if static_file.exists():
            return FileResponse(static_file)
        return HTMLResponse("<h1>HIS.Pro</h1><p>Frontend not built yet</p>", status_code=200)
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        from app.extensions import engine
        health_status = {"status": "healthy"}

        # Check database connection
        try:
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            health_status["database"] = "connected"
        except Exception as e:
            health_status["database"] = f"error: {str(e)}"
            health_status["status"] = "unhealthy"

        # Check Redis
        if redis_client:
            try:
                redis_client.ping()
                health_status["redis"] = "connected"
            except Exception as e:
                health_status["redis"] = f"error: {str(e)}"
                health_status["status"] = "degraded"
        else:
            health_status["redis"] = "not configured"

        return health_status
    
    # Catch-all for SPA routes (must be last)
    @app.get("/{full_path:path}", response_class=HTMLResponse)
    async def serve_spa(full_path: str):
        """Serve index.html for all frontend routes (SPA fallback)"""
        # Don't intercept API routes
        if full_path.startswith(('api/', 'docs', 'redoc', 'openapi.json', 'static')):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")
        
        # Serve index.html for all other routes
        from fastapi.responses import FileResponse
        import pathlib
        
        static_file = pathlib.Path(STATIC_FOLDER) / 'index.html'
        if static_file.exists():
            return FileResponse(static_file)
        return HTMLResponse("<h1>HIS.Pro</h1><p>Page not found</p>", status_code=404)
    
    return app


# Create the app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if os.getenv('FLASK_ENV') == 'development' else False,
        workers=4
    )