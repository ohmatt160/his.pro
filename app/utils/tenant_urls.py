import hashlib
import re


CANONICAL_SUBDOMAIN_MAX_LENGTH = 63
RESERVED_CANONICAL_SUBDOMAINS = frozenset(
    {
        "admin",
        "api",
        "app",
        "assets",
        "auth",
        "cdn",
        "help",
        "mail",
        "static",
        "status",
        "support",
        "www",
    }
)
_DNS_LABEL_PATTERN = re.compile(
    rf"^[a-z0-9](?:[a-z0-9-]{{0,{CANONICAL_SUBDOMAIN_MAX_LENGTH - 2}}}[a-z0-9])?$"
)
_FACILITY_SLUG_PATTERN = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,98}[a-z0-9])?$"
)


def is_valid_facility_slug(value: str) -> bool:
    return bool(_FACILITY_SLUG_PATTERN.fullmatch(str(value or "").strip().lower()))


def is_valid_canonical_subdomain(value: str) -> bool:
    normalized = str(value or "").strip().lower()
    return bool(
        normalized
        and normalized not in RESERVED_CANONICAL_SUBDOMAINS
        and _DNS_LABEL_PATTERN.fullmatch(normalized)
    )


def generate_canonical_subdomain(facility_slug: str, facility_id: str) -> str:
    """Return an immutable, DNS-safe label for a facility UUID."""
    normalized_slug = str(facility_slug or "").strip().lower()
    if is_valid_canonical_subdomain(normalized_slug):
        return normalized_slug

    digest = hashlib.sha256(str(facility_id).encode("utf-8")).hexdigest()[:16]
    max_prefix_length = CANONICAL_SUBDOMAIN_MAX_LENGTH - len(digest) - 1
    prefix = re.sub(r"[^a-z0-9-]+", "-", normalized_slug)
    prefix = re.sub(r"-+", "-", prefix).strip("-")[:max_prefix_length].rstrip("-")
    if not prefix or prefix in RESERVED_CANONICAL_SUBDOMAINS:
        prefix = "facility"

    return f"{prefix}-{digest}"
