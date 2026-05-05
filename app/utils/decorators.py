from functools import wraps
from flask import request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.models.user import User
from app.extensions import db

def role_required(*roles):
    """Decorator to require specific roles for endpoint access"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            verify_jwt_in_request()
            current_user_id = get_jwt_identity()
            user = db.session.get(User, current_user_id)
            
            if not user or user.role not in roles:
                return {
                    'error': {
                        'message': 'Access forbidden. Insufficient permissions.',
                        'status': 403
                    }
                }, 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def token_required(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        verify_jwt_in_request()
        return f(*args, **kwargs)
    return decorated_function
