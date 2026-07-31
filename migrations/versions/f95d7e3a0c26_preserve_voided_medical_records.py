"""preserve voided medical records

Revision ID: f95d7e3a0c26
Revises: e84a6c2d9b15
"""

from alembic import op
import sqlalchemy as sa


revision = "f95d7e3a0c26"
down_revision = "e84a6c2d9b15"
branch_labels = None
depends_on = None


def _column_names() -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("medical_records")
    }


def _index_names() -> set[str]:
    return {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes("medical_records")
        if index.get("name")
    }


def _has_voided_by_foreign_key() -> bool:
    return any(
        foreign_key.get("referred_table") == "users"
        and foreign_key.get("constrained_columns") == ["voided_by"]
        for foreign_key in sa.inspect(op.get_bind()).get_foreign_keys(
            "medical_records"
        )
    )


def upgrade():
    columns = _column_names()
    indexes = _index_names()
    has_voided_by_foreign_key = _has_voided_by_foreign_key()
    with op.batch_alter_table("medical_records") as batch_op:
        if "status" not in columns:
            batch_op.add_column(
                sa.Column(
                    "status",
                    sa.String(length=20),
                    nullable=False,
                    server_default="ACTIVE",
                )
            )
        if "void_reason" not in columns:
            batch_op.add_column(sa.Column("void_reason", sa.Text(), nullable=True))
        if "voided_at" not in columns:
            batch_op.add_column(sa.Column("voided_at", sa.DateTime(), nullable=True))
        if "voided_by" not in columns:
            batch_op.add_column(
                sa.Column("voided_by", sa.String(length=36), nullable=True)
            )
        if not has_voided_by_foreign_key:
            batch_op.create_foreign_key(
                "fk_medical_records_voided_by_users",
                "users",
                ["voided_by"],
                ["id"],
            )
        if "idx_medical_records_facility_status_created" not in indexes:
            batch_op.create_index(
                "idx_medical_records_facility_status_created",
                ["facility_slug", "status", "created_at"],
                unique=False,
            )
        if "ix_medical_records_status" not in indexes:
            batch_op.create_index(
                "ix_medical_records_status",
                ["status"],
                unique=False,
            )


def downgrade():
    columns = _column_names()
    indexes = _index_names()
    has_voided_by_foreign_key = _has_voided_by_foreign_key()
    with op.batch_alter_table("medical_records") as batch_op:
        if "ix_medical_records_status" in indexes:
            batch_op.drop_index("ix_medical_records_status")
        if "idx_medical_records_facility_status_created" in indexes:
            batch_op.drop_index("idx_medical_records_facility_status_created")
        if has_voided_by_foreign_key:
            foreign_key = next(
                foreign_key
                for foreign_key in sa.inspect(op.get_bind()).get_foreign_keys(
                    "medical_records"
                )
                if foreign_key.get("referred_table") == "users"
                and foreign_key.get("constrained_columns") == ["voided_by"]
            )
            if foreign_key.get("name"):
                batch_op.drop_constraint(foreign_key["name"], type_="foreignkey")
        if "voided_by" in columns:
            batch_op.drop_column("voided_by")
        if "voided_at" in columns:
            batch_op.drop_column("voided_at")
        if "void_reason" in columns:
            batch_op.drop_column("void_reason")
        if "status" in columns:
            batch_op.drop_column("status")
