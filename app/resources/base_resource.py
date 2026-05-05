from flask import request
from flask_restx import Resource
from flask_jwt_extended import get_jwt_identity
from app.models.user import User
from app.utils.decorators import token_required

class BaseResource(Resource):
    """Base resource class with common functionality"""
    
    # Token required by default for all methods - public endpoints override with @auth_ns.doc(security=None)
    method_decorators = [token_required]
    
    def get_current_user(self):
        """Get current authenticated user"""
        from app.extensions import db
        user_id = get_jwt_identity()
        return db.session.get(User, user_id)
    
    def handle_response(self, data=None, message=None, status_code=200):
        """Standardized response handler"""
        response = {}
        if data is not None:
            response['data'] = data
        if message is not None:
            response['message'] = message
        return response, status_code
    
    def handle_error(self, error_message, status_code=400):
        """Standardized error handler matching APIError format"""
        return {
            'error': {
                'message': error_message,
                'status': status_code
            }
        }, status_code
