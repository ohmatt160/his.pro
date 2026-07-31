"""add clinical write idempotency

Revision ID: b17f9a5c8d20
Revises: a06e8f4b7c19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "b17f9a5c8d20"
down_revision = "a06e8f4b7c19"
branch_labels = None
depends_on = None


TABLES = (
    ("appointments", "uq_appointments_facility_idempotency"),
    ("medical_records", "uq_medical_records_facility_idempotency"),
    ("lab_orders", "uq_lab_orders_facility_idempotency"),
    ("prescriptions", "uq_prescriptions_facility_idempotency"),
)


def _columns(table_name: str) -> set[str]:
    return {
        column["name"]
        for column in inspect(op.get_bind()).get_columns(table_name)
    }


def _indexes(table_name: str) -> set[str]:
    return {
        index["name"]
        for index in inspect(op.get_bind()).get_indexes(table_name)
        if index.get("name")
    }


def upgrade():
    for table_name, index_name in TABLES:
        columns = _columns(table_name)
        with op.batch_alter_table(table_name) as batch_op:
            if "idempotency_key" not in columns:
                batch_op.add_column(
                    sa.Column("idempotency_key", sa.String(length=200), nullable=True)
                )
            if "idempotency_payload_hash" not in columns:
                batch_op.add_column(
                    sa.Column(
                        "idempotency_payload_hash",
                        sa.String(length=64),
                        nullable=True,
                    )
                )
        if index_name not in _indexes(table_name):
            op.create_index(
                index_name,
                table_name,
                ["facility_slug", "idempotency_key"],
                unique=True,
            )


def downgrade():
    for table_name, index_name in reversed(TABLES):
        if index_name in _indexes(table_name):
            op.drop_index(index_name, table_name=table_name)
        columns = _columns(table_name)
        with op.batch_alter_table(table_name) as batch_op:
            if "idempotency_payload_hash" in columns:
                batch_op.drop_column("idempotency_payload_hash")
            if "idempotency_key" in columns:
                batch_op.drop_column("idempotency_key")
