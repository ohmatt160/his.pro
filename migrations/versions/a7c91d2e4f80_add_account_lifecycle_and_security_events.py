"""add account lifecycle controls and privacy-preserving security events

Revision ID: a7c91d2e4f80
Revises: f51d8a2b6c74
"""

from alembic import op
import sqlalchemy as sa


revision = "a7c91d2e4f80"
down_revision = "f51d8a2b6c74"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table_name: str) -> set[str]:
    if table_name not in _table_names():
        return set()
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    if table_name not in _table_names():
        return set()
    return {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes(table_name)
        if index.get("name")
    }


def _create_index_if_missing(name: str, table_name: str, columns: list[str]) -> None:
    if name not in _index_names(table_name):
        op.create_index(name, table_name, columns)


def upgrade():
    facility_columns = _columns("facilities")
    if "deletion_status" not in facility_columns:
        op.add_column(
            "facilities",
            sa.Column(
                "deletion_status",
                sa.String(length=24),
                nullable=False,
                server_default=sa.text("'ACTIVE'"),
            ),
        )
    for name in (
        "deletion_requested_at",
        "deletion_scheduled_for",
        "deletion_cancelled_at",
    ):
        if name not in facility_columns:
            op.add_column("facilities", sa.Column(name, sa.DateTime(), nullable=True))
    if "deletion_requested_by_id" not in facility_columns:
        op.add_column(
            "facilities",
            sa.Column("deletion_requested_by_id", sa.String(length=36), nullable=True),
        )
        if op.get_bind().dialect.name != "sqlite":
            op.create_foreign_key(
                "fk_facilities_deletion_requested_by_user",
                "facilities",
                "users",
                ["deletion_requested_by_id"],
                ["id"],
            )
    if "deletion_recovery_token_hash" not in facility_columns:
        op.add_column(
            "facilities",
            sa.Column("deletion_recovery_token_hash", sa.String(length=64), nullable=True),
        )
    _create_index_if_missing("ix_facilities_deletion_status", "facilities", ["deletion_status"])
    _create_index_if_missing(
        "ix_facilities_deletion_scheduled_for",
        "facilities",
        ["deletion_scheduled_for"],
    )

    if "security_events" not in _table_names():
        op.create_table(
            "security_events",
            sa.Column("facility_id", sa.String(length=36), nullable=True),
            sa.Column("facility_slug", sa.String(length=100), nullable=True),
            sa.Column("subject_hash", sa.String(length=64), nullable=False),
            sa.Column("category", sa.String(length=64), nullable=False),
            sa.Column("rule_id", sa.String(length=100), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=False),
            sa.Column("action", sa.String(length=20), nullable=False),
            sa.Column("method", sa.String(length=10), nullable=False),
            sa.Column("endpoint_hash", sa.String(length=64), nullable=False),
            sa.Column("response_status", sa.Integer(), nullable=True),
            sa.Column("score", sa.Integer(), nullable=False),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
            sa.ForeignKeyConstraint(["facility_slug"], ["facilities.slug"]),
            sa.PrimaryKeyConstraint("id"),
        )
    for name, columns in (
        ("ix_security_events_facility_id", ["facility_id"]),
        ("ix_security_events_facility_slug", ["facility_slug"]),
        ("ix_security_events_subject_hash", ["subject_hash"]),
        ("ix_security_events_category", ["category"]),
        ("ix_security_events_rule_id", ["rule_id"]),
        ("ix_security_events_severity", ["severity"]),
        ("ix_security_events_action", ["action"]),
        ("ix_security_events_created_at", ["created_at"]),
        ("idx_security_events_facility_created", ["facility_id", "created_at"]),
        ("idx_security_events_subject_created", ["subject_hash", "created_at"]),
        ("idx_security_events_action_created", ["action", "created_at"]),
    ):
        _create_index_if_missing(name, "security_events", columns)


def downgrade():
    if "security_events" in _table_names():
        op.drop_table("security_events")

    facility_columns = _columns("facilities")
    for name in (
        "ix_facilities_deletion_scheduled_for",
        "ix_facilities_deletion_status",
    ):
        if name in _index_names("facilities"):
            op.drop_index(name, table_name="facilities")
    if op.get_bind().dialect.name != "sqlite" and "deletion_requested_by_id" in facility_columns:
        op.drop_constraint(
            "fk_facilities_deletion_requested_by_user",
            "facilities",
            type_="foreignkey",
        )
    with op.batch_alter_table("facilities") as batch_op:
        for name in (
            "deletion_recovery_token_hash",
            "deletion_requested_by_id",
            "deletion_cancelled_at",
            "deletion_scheduled_for",
            "deletion_requested_at",
            "deletion_status",
        ):
            if name in facility_columns:
                batch_op.drop_column(name)
