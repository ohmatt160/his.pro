"""
Custom error handling for FastAPI
Converted from Flask error handlers
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
import logging

logger = logging.getLogger(__name__)

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
    """Register error handlers with the FastAPI app"""

    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exc: APIError):
        """Handle custom API errors"""
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict()
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                'error': {
                    'message': exc.detail,
                    'code': exc.status_code,
                    'status': exc.status_code
                }
            }
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        """Handle FastAPI/Pydantic validation errors"""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                'error': {
                    'message': 'Validation error',
                    'code': ErrorCodes.VALIDATION_ERROR,
                    'status': 400,
                    'details': exc.errors()
                }
            }
        )

    @app.exception_handler(ValidationError)
    async def handle_marshmallow_error(request: Request, exc: ValidationError):
        """Handle marshmallow validation errors (if still used)"""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                'error': {
                    'message': 'Validation error',
                    'code': ErrorCodes.VALIDATION_ERROR,
                    'status': 400,
                    'details': exc.messages
                }
            }
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, exc: IntegrityError):
        """Handle database integrity errors"""
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                'error': {
                    'message': 'Database integrity error',
                    'code': ErrorCodes.DATABASE_INTEGRITY_ERROR,
                    'status': 409,
                    'details': str(exc.orig)
                }
            }
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(request: Request, exc: SQLAlchemyError):
        """Handle database errors"""
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                'error': {
                    'message': 'Database error',
                    'code': ErrorCodes.DATABASE_ERROR,
                    'status': 500,
                    'details': str(exc)
                }
            }
        )

    @app.exception_handler(ExpiredSignatureError)
    async def handle_expired_token(request: Request, exc: ExpiredSignatureError):
        """Handle expired JWT tokens"""
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                'error': {
                    'message': 'Token has expired',
                    'code': ErrorCodes.AUTH_TOKEN_EXPIRED,
                    'status': 401
                }
            }
        )

    @app.exception_handler(InvalidTokenError)
    async def handle_invalid_token(request: Request, exc: InvalidTokenError):
        """Handle invalid JWT tokens"""
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                'error': {
                    'message': 'Invalid token',
                    'code': ErrorCodes.AUTH_TOKEN_INVALID,
                    'status': 401
                }
            }
        )

    @app.exception_handler(Exception)
    async def handle_generic_error(request: Request, exc: Exception):
        """Handle all other exceptions"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                'error': {
                    'message': 'Internal server error',
                    'code': ErrorCodes.SERVER_INTERNAL_ERROR,
                    'status': 500
                }
            }
        )
