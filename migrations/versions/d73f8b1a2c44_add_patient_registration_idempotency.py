"""add patient registration idempotency

Revision ID: d73f8b1a2c44
Revises: c42e7a9d5f11
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa


revision = "d73f8b1a2c44"
down_revision = "c42e7a9d5f11"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def _index_names(table_name: str) -> set[str]:
    return {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes(table_name)
        if index.get("name")
    }


def upgrade():
    columns = _column_names("patients")
    if "registration_idempotency_key" not in columns:
        with op.batch_alter_table("patients") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "registration_idempotency_key",
                    sa.String(length=200),
                    nullable=True,
                )
            )
    if "registration_payload_hash" not in columns:
        with op.batch_alter_table("patients") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "registration_payload_hash",
                    sa.String(length=64),
                    nullable=True,
                )
            )
    if "uq_patients_facility_registration_idempotency" not in _index_names("patients"):
        op.create_index(
            "uq_patients_facility_registration_idempotency",
            "patients",
            ["facility_slug", "registration_idempotency_key"],
            unique=True,
        )


def downgrade():
    if "uq_patients_facility_registration_idempotency" in _index_names("patients"):
        op.drop_index(
            "uq_patients_facility_registration_idempotency",
            table_name="patients",
        )
    columns = _column_names("patients")
    with op.batch_alter_table("patients") as batch_op:
        if "registration_payload_hash" in columns:
            batch_op.drop_column("registration_payload_hash")
        if "registration_idempotency_key" in columns:
            batch_op.drop_column("registration_idempotency_key")
