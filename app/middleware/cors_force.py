from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Scope, Receive, Send


class ForceCORSHeadersMiddleware:
    """Force CORS headers on every response - bypasses HF proxy stripping"""

    def __init__(self, app: ASGIApp, allowed_origins: list):
        self.app = app
        self.allowed_origins = allowed_origins

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        origin = None
        for header in scope.get("headers", []):
            if header[0] == b"origin":
                origin = header[1].decode()
                break

        async def send_with_cors(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                if origin in self.allowed_origins:
                    headers[b"access-control-allow-origin"] = origin.encode()
                    headers[b"access-control-allow-credentials"] = b"true"
                if scope["method"] == "OPTIONS":
                    headers[b"access-control-allow-methods"] = b"GET, POST, PUT, DELETE, OPTIONS, PATCH"
                    headers[b"access-control-allow-headers"] = b"Content-Type, Authorization, Accept"
                    headers[b"access-control-max-age"] = b"600"
                message["headers"] = list(headers.items())
            await send(message)

        await self.app(scope, receive, send_with_cors)