"""Network identity helpers that do not trust spoofable forwarding headers."""

from __future__ import annotations

import ipaddress
import os

from fastapi import Request


def _trusted_proxy_addresses() -> set[str]:
    return {
        value.strip()
        for value in os.getenv("TRUSTED_PROXY_IPS", "").split(",")
        if value.strip()
    }


def proxy_headers_are_trusted(request: Request) -> bool:
    direct_ip = request.client.host if request.client else ""
    if os.getenv("TRUST_PROXY_HEADERS", "").lower() == "true":
        return True
    return direct_ip in _trusted_proxy_addresses()


def _valid_ip(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def client_ip(request: Request) -> str:
    """Return an address only from an explicitly trusted proxy chain."""
    if proxy_headers_are_trusted(request):
        forwarded_for = request.headers.get("x-forwarded-for", "")
        for candidate in forwarded_for.split(","):
            parsed = _valid_ip(candidate)
            if parsed:
                return parsed
        parsed = _valid_ip(request.headers.get("x-real-ip"))
        if parsed:
            return parsed
    return _valid_ip(request.client.host if request.client else None) or "unknown"
