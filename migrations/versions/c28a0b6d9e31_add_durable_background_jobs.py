"""add durable background jobs

Revision ID: c28a0b6d9e31
Revises: b17f9a5c8d20
"""

from alembic import op
import sqlalchemy as sa


revision = "c28a0b6d9e31"
down_revision = "b17f9a5c8d20"
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
    if name not in _index_names("background_jobs"):
        op.create_index(name, "background_jobs", columns)


def upgrade():
    if not _table_exists("background_jobs"):
        op.create_table(
            "background_jobs",
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("facility_id", sa.String(length=36), nullable=False),
            sa.Column("requested_by_user_id", sa.String(length=36), nullable=False),
            sa.Column("idempotency_key", sa.String(length=200), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("max_attempts", sa.Integer(), nullable=False),
            sa.Column("available_at", sa.DateTime(), nullable=False),
            sa.Column("locked_at", sa.DateTime(), nullable=True),
            sa.Column("lock_owner", sa.String(length=160), nullable=True),
            sa.Column("result_json", sa.JSON(), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("external_job_id", sa.String(length=200), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
            sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "facility_id",
                "name",
                "idempotency_key",
                name="uq_background_jobs_tenant_name_idempotency",
            ),
        )
    _create_index_if_missing("ix_background_jobs_facility_id", ["facility_id"])
    _create_index_if_missing(
        "ix_background_jobs_requested_by_user_id",
        ["requested_by_user_id"],
    )
    _create_index_if_missing(
        "idx_background_jobs_claim",
        ["status", "available_at", "created_at"],
    )
    _create_index_if_missing(
        "idx_background_jobs_tenant_status",
        ["facility_id", "status", "created_at"],
    )
    _create_index_if_missing(
        "idx_background_jobs_lease",
        ["status", "locked_at"],
    )


def downgrade():
    if _table_exists("background_jobs"):
        op.drop_table("background_jobs")
