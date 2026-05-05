"""
Custom error handling utilities for the HIS.Pro API
"""

from flask import jsonify, request
from werkzeug.exceptions import HTTPException
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
import traceback

# Custom error codes
class ErrorCodes:
    """Custom error codes for the API"""
    
    # Authentication errors (1000-1999)
    AUTH_INVALID_CREDENTIALS = 1001
    AUTH_TOKEN_EXPIRED = 1002
    AUTH_TOKEN_INVALID = 1003
    AUTH_ACCESS_DENIED = 1004
    AUTH_USER_NOT_FOUND = 1005
    AUTH_USER_ALREADY_EXISTS = 1006
    AUTH_PASSWORD_TOO_WEAK = 1007
    AUTH_EMAIL_ALREADY_EXISTS = 1008
    
    # Validation errors (2000-2999)
    VALIDATION_ERROR = 2001
    VALIDATION_REQUIRED_FIELD = 2002
    VALIDATION_INVALID_FORMAT = 2003
    VALIDATION_INVALID_LENGTH = 2004
    VALIDATION_INVALID_VALUE = 2005
    
    # Resource errors (3000-3999)
    RESOURCE_NOT_FOUND = 3001
    RESOURCE_ALREADY_EXISTS = 3002
    RESOURCE_CONFLICT = 3003
    RESOURCE_GONE = 3004
    
    # Database errors (4000-4999)
    DATABASE_ERROR = 4001
    DATABASE_INTEGRITY_ERROR = 4002
    DATABASE_CONNECTION_ERROR = 4003
    
    # Server errors (5000-5999)
    SERVER_INTERNAL_ERROR = 5001
    SERVER_NOT_IMPLEMENTED = 5002
    SERVER_SERVICE_UNAVAILABLE = 5003
    
    # Rate limiting errors (6000-6999)
    RATE_LIMIT_EXCEEDED = 6001
    
    # File upload errors (7000-7999)
    FILE_UPLOAD_ERROR = 7001
    FILE_TOO_LARGE = 7002
    FILE_TYPE_NOT_ALLOWED = 7003
    FILE_NOT_FOUND = 7004


class APIError(Exception):
    """Custom API error class"""
    
    def __init__(self, message, status_code=400, error_code=None, details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
    
    def to_dict(self):
        error_dict = {
            'error': {
                'message': self.message,
                'code': self.error_code,
                'status': self.status_code
            }
        }
        if self.details:
            error_dict['error']['details'] = self.details
        return error_dict


class AuthenticationError(APIError):
    """Authentication related errors"""
    
    def __init__(self, message, error_code=ErrorCodes.AUTH_INVALID_CREDENTIALS, details=None):
        super().__init__(message, status_code=401, error_code=error_code, details=details)


class AuthorizationError(APIError):
    """Authorization related errors"""
    
    def __init__(self, message, error_code=ErrorCodes.AUTH_ACCESS_DENIED, details=None):
        super().__init__(message, status_code=403, error_code=error_code, details=details)


class ValidationError(APIError):
    """Validation related errors"""
    
    def __init__(self, message, error_code=ErrorCodes.VALIDATION_ERROR, details=None):
        super().__init__(message, status_code=400, error_code=error_code, details=details)


class ResourceNotFoundError(APIError):
    """Resource not found errors"""
    
    def __init__(self, message, error_code=ErrorCodes.RESOURCE_NOT_FOUND, details=None):
        super().__init__(message, status_code=404, error_code=error_code, details=details)


class ResourceConflictError(APIError):
    """Resource conflict errors"""
    
    def __init__(self, message, error_code=ErrorCodes.RESOURCE_CONFLICT, details=None):
        super().__init__(message, status_code=409, error_code=error_code, details=details)


class DatabaseError(APIError):
    """Database related errors"""
    
    def __init__(self, message, error_code=ErrorCodes.DATABASE_ERROR, details=None):
        super().__init__(message, status_code=500, error_code=error_code, details=details)


class RateLimitError(APIError):
    """Rate limiting errors"""
    
    def __init__(self, message, error_code=ErrorCodes.RATE_LIMIT_EXCEEDED, details=None):
        super().__init__(message, status_code=429, error_code=error_code, details=details)


class FileUploadError(APIError):
    """File upload related errors"""
    
    def __init__(self, message, error_code=ErrorCodes.FILE_UPLOAD_ERROR, details=None):
        super().__init__(message, status_code=400, error_code=error_code, details=details)


def register_error_handlers(app):
    """Register error handlers with the Flask app"""
    
    @app.errorhandler(APIError)
    def handle_api_error(error):
        """Handle custom API errors"""
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response
    
    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        """Handle HTTP exceptions"""
        response = jsonify({
            'error': {
                'message': error.description,
                'code': error.code,
                'status': error.code
            }
        })
        response.status_code = error.code
        return response
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        """Handle marshmallow validation errors"""
        response = jsonify({
            'error': {
                'message': 'Validation error',
                'code': ErrorCodes.VALIDATION_ERROR,
                'status': 400,
                'details': error.messages
            }
        })
        response.status_code = 400
        return response
    
    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error):
        """Handle database integrity errors"""
        response = jsonify({
            'error': {
                'message': 'Database integrity error',
                'code': ErrorCodes.DATABASE_INTEGRITY_ERROR,
                'status': 409,
                'details': str(error.orig)
            }
        })
        response.status_code = 409
        return response
    
    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(error):
        """Handle database errors"""
        response = jsonify({
            'error': {
                'message': 'Database error',
                'code': ErrorCodes.DATABASE_ERROR,
                'status': 500,
                'details': str(error)
            }
        })
        response.status_code = 500
        return response
    
    @app.errorhandler(ExpiredSignatureError)
    def handle_expired_token(error):
        """Handle expired JWT tokens"""
        response = jsonify({
            'error': {
                'message': 'Token has expired',
                'code': ErrorCodes.AUTH_TOKEN_EXPIRED,
                'status': 401
            }
        })
        response.status_code = 401
        return response
    
    @app.errorhandler(InvalidTokenError)
    def handle_invalid_token(error):
        """Handle invalid JWT tokens"""
        response = jsonify({
            'error': {
                'message': 'Invalid token',
                'code': ErrorCodes.AUTH_TOKEN_INVALID,
                'status': 401
            }
        })
        response.status_code = 401
        return response
    
    @app.errorhandler(Exception)
    def handle_generic_error(error):
        """Handle all other exceptions"""
        # Log the error for debugging
        app.logger.error(f"Unhandled exception: {error}")
        app.logger.error(traceback.format_exc())
        
        response = jsonify({
            'error': {
                'message': 'Internal server error',
                'code': ErrorCodes.SERVER_INTERNAL_ERROR,
                'status': 500
            }
        })
        response.status_code = 500
        return response


def create_error_response(message, status_code=400, error_code=None, details=None):
    """Create a standardized error response"""
    error_dict = {
        'error': {
            'message': message,
            'code': error_code,
            'status': status_code
        }
    }
    if details:
        error_dict['error']['details'] = details
    return jsonify(error_dict), status_code


def create_success_response(data=None, message=None, status_code=200):
    """Create a standardized success response"""
    response_dict = {}
    if data is not None:
        response_dict['data'] = data
    if message is not None:
        response_dict['message'] = message
    return jsonify(response_dict), status_code
