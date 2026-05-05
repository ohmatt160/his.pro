from flask import Flask, send_file, redirect, g
import os
import pathlib

# Import extensions
from app.extensions import db, migrate, jwt, cors
from app.services.email_service import EmailService
from app.utils.rate_limiter import init_rate_limiter
from app.utils.error_handlers import register_error_handlers
from flask_restx import Api

# Import namespaces
from app.resources.auth_resource import auth_ns
from app.resources.patient_resource import patient_ns
from app.resources.appointment_resource import appointment_ns
from app.resources.lab_resource import lab_ns
from app.resources.pharmacy_resource import pharmacy_ns
from app.resources.billing_resource import billing_ns
from app.resources.medical_record_resource import emr_ns
from app.resources.user_profile_resource import user_profile_ns
from app.resources.password_reset_resource import password_reset_ns
from app.resources.file_upload_resource import file_upload_ns
from app.resources.audit_log_resource import audit_log_ns
from app.resources.facility_resource import facility_ns
from app.resources.radiology_resource import radiology_ns
from app.resources.inventory_resource import inventory_ns
from app.resources.queue_resource import queue_ns
from app.resources.alert_resource import alert_ns
from app.resources.dashboard_resource import dashboard_ns

# JWT token blocklist (supports both in-memory and Redis)
import os
import redis

# Determine if we should use Redis for blocklist
USE_REDIS = os.getenv('REDIS_URL', '') != ''

if USE_REDIS:
    # Production: Use Redis for distributed blocklist
    redis_client = redis.from_url(os.getenv('REDIS_URL'))
    
    class JWTBlocklist:
        """Redis-based JWT blocklist for production"""
        
        @staticmethod
        def add(jti: str):
            """Add token to blocklist"""
            redis_client.setex(f"jwt_blocklist:{jti}", 86400, "1")  # 24hr TTL
        
        @staticmethod
        def is_blocklisted(jti: str) -> bool:
            """Check if token is blocklisted"""
            return redis_client.exists(f"jwt_blocklist:{jti}") > 0
    
    jwt_blocklist = JWTBlocklist()
else:
    # Development: Use in-memory set
    jwt_blocklist_set = set()
    
    class JWTBlocklist:
        """In-memory JWT blocklist for development"""
        
        @staticmethod
        def add(jti: str):
            """Add token to blocklist"""
            jwt_blocklist_set.add(jti)
        
        @staticmethod
        def is_blocklisted(jti: str) -> bool:
            """Check if token is blocklisted"""
            return jti in jwt_blocklist_set
    
    jwt_blocklist = JWTBlocklist()

# Store static folder path globally
STATIC_FOLDER = None

def create_app(config_name='default'):
    global STATIC_FOLDER
    
    # Get the base directory - __file__ is app/__init__.py, so go up one level to workspace root
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    # Static files are in app/static
    static_folder = os.path.join(base_dir, 'app', 'static')
    
    STATIC_FOLDER = static_folder
    
    # Create Flask app with static folder configured
    # Use static_url_path='' to serve at root (/) but path can be anything
    app = Flask(__name__,
                static_folder=static_folder,
                static_url_path='')
    
    # Load configuration
    from config import config
    app.config.from_object(config[config_name])
    
    # Check required env vars for production
    if config_name == 'production':
        config[config_name].__init__()
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    
    # Configure CORS with allowed origins from environment
    allowed_origins = os.getenv('ALLOWED_ORIGINS', '').split(',') if os.getenv('ALLOWED_ORIGINS') else []
    # Default to specific origins in production, allow all in dev
    if config_name == 'production' and not allowed_origins:
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
    
    cors.init_app(app, resources={
        r"/*": {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            "allow_headers": ["Content-Type", "Authorization", "Accept"],
            "supports_credentials": True,
            "expose_headers": ["Authorization"],
        }
    })
    
    # Configure JWT blocklist callback
    @jwt.token_in_blocklist_loader
    def check_if_token_is_revoked(jwt_header, jwt_payload):
        jti = jwt_payload['jti']
        # Use the is_blocklisted method for proper checking
        return jwt_blocklist.is_blocklisted(jti)
    
    # Initialize email service
    EmailService.init_app(app)
    
    # Initialize rate limiter
    init_rate_limiter(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    @app.route('/health')
    def health():
        return {'status': 'healthy'}, 200
    
    # Initialize API with Swagger - catch_all_controllers=False
    api = Api(
        app,
        title='HIS.Pro API',
        version='1.0',
        description='Health Information System API',
        doc='/docs',
        catch_all_controllers=False,
        prefix='/api/v1'
    )
    
    # Register namespaces
    api.add_namespace(auth_ns, path='/auth')
    api.add_namespace(patient_ns, path='/patients')
    api.add_namespace(appointment_ns, path='/appointments')
    api.add_namespace(lab_ns, path='/laboratory')
    api.add_namespace(pharmacy_ns, path='/pharmacy')
    api.add_namespace(billing_ns, path='/billing')
    api.add_namespace(emr_ns, path='/emr')
    api.add_namespace(user_profile_ns, path='/users')
    api.add_namespace(password_reset_ns, path='/password-reset')
    api.add_namespace(file_upload_ns, path='/files')
    api.add_namespace(audit_log_ns, path='/audit-logs')
    api.add_namespace(facility_ns, path='/facilities')
    api.add_namespace(radiology_ns, path='/radiology')
    api.add_namespace(inventory_ns, path='/inventory')
    api.add_namespace(queue_ns, path='/queue')
    api.add_namespace(alert_ns, path='/alerts')
    api.add_namespace(dashboard_ns, path='/dashboard')
    
    # Serve index.html for root path
    @app.route('/', methods=['GET', 'HEAD'])
    def serve_index():
        # Force no caching to prevent stale redirects
        from flask import make_response
        response = make_response(send_file(pathlib.Path(STATIC_FOLDER) / 'index.html'))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, proxy-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['Surrogate-Control'] = 'no-store'
        return response
    
    # Explicit routes for main frontend pages (these MUST be registered)
    @app.route('/get-started', methods=['GET', 'HEAD'])
    @app.route('/login', methods=['GET', 'HEAD'])
    @app.route('/login/<slug>', methods=['GET', 'HEAD'])
    @app.route('/setting-up', methods=['GET', 'HEAD'])
    @app.route('/workspace-ready/<slug>', methods=['GET', 'HEAD'])
    @app.route('/dashboard/<slug>/staff', methods=['GET', 'HEAD'])
    @app.route('/dashboard/<slug>', methods=['GET', 'HEAD'])
    def serve_frontend_pages(**kwargs):
        """Serve index.html for all frontend routes"""
        from flask import make_response
        response = make_response(send_file(pathlib.Path(STATIC_FOLDER) / 'index.html'))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, proxy-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['Surrogate-Control'] = 'no-store'
        return response
    
    # Catch-all for any other SPA routes not explicitly defined above
    @app.route('/<path:fallback>', methods=['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'PATCH'])
    def serve_spa(fallback):
        # Don't intercept API routes
        if fallback.startswith('api/') or fallback.startswith('docs') or fallback.startswith('swagger'):
            from flask import abort
            return abort(404)
        
        from flask import make_response
        response = make_response(send_file(pathlib.Path(STATIC_FOLDER) / 'index.html'))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, proxy-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['Surrogate-Control'] = 'no-store'
        return response
    
    return app
