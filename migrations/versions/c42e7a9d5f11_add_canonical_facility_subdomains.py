"""add immutable canonical facility subdomains

Revision ID: c42e7a9d5f11
Revises: b91f6a2c4d30
Create Date: 2026-07-27
"""

import hashlib
import re

from alembic import op
import sqlalchemy as sa


revision = "c42e7a9d5f11"
down_revision = "b91f6a2c4d30"
branch_labels = None
depends_on = None


RESERVED_SUBDOMAINS = {
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
DNS_LABEL_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def _canonical_subdomain(facility_slug: str, facility_id: str) -> str:
    slug = str(facility_slug or "").strip().lower()
    if slug not in RESERVED_SUBDOMAINS and DNS_LABEL_PATTERN.fullmatch(slug):
        return slug

    digest = hashlib.sha256(str(facility_id).encode("utf-8")).hexdigest()[:16]
    prefix = re.sub(r"[^a-z0-9-]+", "-", slug)
    prefix = re.sub(r"-+", "-", prefix).strip("-")[:46].rstrip("-")
    if not prefix or prefix in RESERVED_SUBDOMAINS:
        prefix = "facility"
    return f"{prefix}-{digest}"


def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {
        column["name"]: column
        for column in inspector.get_columns("facilities")
    }
    if "canonical_subdomain" not in columns:
        op.add_column(
            "facilities",
            sa.Column("canonical_subdomain", sa.String(length=63), nullable=True),
        )

    facilities = sa.table(
        "facilities",
        sa.column("id", sa.String(length=36)),
        sa.column("slug", sa.String(length=100)),
        sa.column("canonical_subdomain", sa.String(length=63)),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(
            facilities.c.id,
            facilities.c.slug,
            facilities.c.canonical_subdomain,
        )
    ).all()
    for facility_id, facility_slug, canonical_subdomain in rows:
        if canonical_subdomain:
            continue
        connection.execute(
            facilities.update()
            .where(facilities.c.id == facility_id)
            .values(
                canonical_subdomain=_canonical_subdomain(
                    str(facility_slug or ""),
                    str(facility_id),
                )
            )
        )

    refreshed_columns = {
        column["name"]: column
        for column in sa.inspect(op.get_bind()).get_columns("facilities")
    }
    index_names = {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes("facilities")
        if index.get("name")
    }
    with op.batch_alter_table("facilities") as batch_op:
        if refreshed_columns["canonical_subdomain"].get("nullable", True):
            batch_op.alter_column(
                "canonical_subdomain",
                existing_type=sa.String(length=63),
                nullable=False,
            )
        if "ix_facilities_canonical_subdomain" not in index_names:
            batch_op.create_index(
                "ix_facilities_canonical_subdomain",
                ["canonical_subdomain"],
                unique=True,
            )


def downgrade():
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("facilities")
    }
    if "canonical_subdomain" not in columns:
        return
    index_names = {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes("facilities")
        if index.get("name")
    }
    with op.batch_alter_table("facilities") as batch_op:
        if "ix_facilities_canonical_subdomain" in index_names:
            batch_op.drop_index("ix_facilities_canonical_subdomain")
        batch_op.drop_column("canonical_subdomain")
