"""add tenant-scoped integration outbox

Revision ID: b91f6a2c4d30
Revises: 8c4f2a1d7e90
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa


revision = "b91f6a2c4d30"
down_revision = "8c4f2a1d7e90"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return table_name in set(sa.inspect(op.get_bind()).get_table_names())


def _index_names(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    return {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes(table_name)
        if index.get("name")
    }


def _create_index_if_missing(name: str, columns: list[str]) -> None:
    if name not in _index_names("integration_outbox"):
        op.create_index(name, "integration_outbox", columns, unique=False)


def upgrade():
    if not _table_exists("integration_outbox"):
        op.create_table(
            "integration_outbox",
            sa.Column("facility_id", sa.String(length=36), nullable=False),
            sa.Column("destination", sa.String(length=40), nullable=False),
            sa.Column("event_type", sa.String(length=100), nullable=False),
            sa.Column("aggregate_type", sa.String(length=80), nullable=True),
            sa.Column("aggregate_id", sa.String(length=36), nullable=True),
            sa.Column("idempotency_key", sa.String(length=200), nullable=False),
            sa.Column("correlation_id", sa.String(length=36), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("max_attempts", sa.Integer(), nullable=False),
            sa.Column("available_at", sa.DateTime(), nullable=False),
            sa.Column("locked_at", sa.DateTime(), nullable=True),
            sa.Column("lock_owner", sa.String(length=160), nullable=True),
            sa.Column("delivered_at", sa.DateTime(), nullable=True),
            sa.Column("last_error_code", sa.String(length=80), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "destination",
                "facility_id",
                "idempotency_key",
                name="uq_integration_outbox_destination_tenant_idempotency",
            ),
        )
    _create_index_if_missing(
        "ix_integration_outbox_facility_id",
        ["facility_id"],
    )
    _create_index_if_missing(
        "ix_integration_outbox_created_at",
        ["created_at"],
    )
    _create_index_if_missing(
        "idx_integration_outbox_dispatch",
        ["destination", "status", "available_at", "created_at"],
    )
    _create_index_if_missing(
        "idx_integration_outbox_tenant_status",
        ["facility_id", "status", "created_at"],
    )
    _create_index_if_missing(
        "idx_integration_outbox_lease",
        ["status", "locked_at"],
    )


def downgrade():
    if _table_exists("integration_outbox"):
        op.drop_table("integration_outbox")
