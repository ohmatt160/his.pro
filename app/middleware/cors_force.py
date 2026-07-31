import re

from starlette.types import ASGIApp, Scope, Receive, Send


ALLOWED_HEADERS = (
    b"Accept, Authorization, Content-Type, Idempotency-Key, "
    b"X-CSRF-Token, X-HISPro-Authorization, X-Onboarding-Token"
)


class ForceCORSHeadersMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        allowed_origins: list = None,
        allowed_origin_regex: str | None = None,
    ):
        self.app = app
        self.allowed_origins = {origin.rstrip("/") for origin in (allowed_origins or [])}
        self.allowed_origin_regex = (
            re.compile(allowed_origin_regex) if allowed_origin_regex else None
        )

    def _is_allowed_origin(self, origin: str | None) -> bool:
        if not origin:
            return False
        normalized_origin = origin.rstrip("/")
        if normalized_origin in self.allowed_origins:
            return True
        return bool(self.allowed_origin_regex and self.allowed_origin_regex.fullmatch(normalized_origin))

    def _cors_headers(self, origin: str, scope: Scope) -> list[tuple[bytes, bytes]]:
        return [
            (b"access-control-allow-origin", origin.rstrip("/").encode()),
            (b"access-control-allow-credentials", b"true"),
            (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS, PATCH"),
            (b"access-control-allow-headers", ALLOWED_HEADERS),
            (b"access-control-max-age", b"600"),
            (b"vary", b"Origin"),
        ]

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
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() not in {
                        b"access-control-allow-origin",
                        b"access-control-allow-credentials",
                        b"access-control-allow-methods",
                        b"access-control-allow-headers",
                        b"access-control-max-age",
                    }
                ]
                if self._is_allowed_origin(origin):
                    headers.extend(self._cors_headers(origin, scope))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_cors)
