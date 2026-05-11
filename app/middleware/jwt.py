"""
JWT Middleware for FastAPI
Handles token verification and authentication
"""

from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
import jwt
import os
from datetime import datetime, timedelta

# JWT Configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY') or 'your-secret-key-change-in-production'
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
JWT_REFRESH_TOKEN_EXPIRES = 86400  # 24 hours

security = HTTPBearer()


def create_access_token(identity: int, expires_delta: timedelta = None) -> str:
    """
    Create a JWT access token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(seconds=JWT_ACCESS_TOKEN_EXPIRES)
    
    to_encode = {
        "exp": expire,
        "iat": datetime.utcnow(),
        "sub": str(identity),
        "type": "access"
    }
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(identity: int) -> str:
    """
    Create a JWT refresh token
    """
    expire = datetime.utcnow() + timedelta(seconds=JWT_REFRESH_TOKEN_EXPIRES)
    to_encode = {
        "exp": expire,
        "iat": datetime.utcnow(),
        "sub": str(identity),
        "type": "refresh"
    }
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> dict:
    """
    Verify and decode a JWT token
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != token_type:
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


class JWTMiddleware(BaseHTTPMiddleware):
    """
    Middleware to verify JWT tokens on protected routes
    """
    
    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/docs", "/redoc", "/openapi.json", 
            "/api/v1/auth/register", 
            "/api/v1/auth/login",
            "/api/v1/auth/refresh",
            "/health"
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Check for Authorization header
        authorization: str = request.headers.get("Authorization")
        if not authorization:
            return await call_next(request)  # Let route handlers deal with missing auth
        
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                return await call_next(request)
            
            # Verify token
            payload = verify_token(token)
            # Attach user info to request state for use in route handlers
            request.state.user_id = int(payload["sub"])
            request.state.user = payload
            
        except (ValueError, HTTPException):
            # Invalid token format or verification failed
            # Let route handlers deal with authentication errors
            pass
        
        response = await call_next(request)
        return response