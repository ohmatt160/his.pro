"""harden patient queue writes

Revision ID: d39b1c7e0f42
Revises: c28a0b6d9e31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "d39b1c7e0f42"
down_revision = "c28a0b6d9e31"
branch_labels = None
depends_on = None


def upgrade():
    columns = {
        column["name"]
        for column in inspect(op.get_bind()).get_columns("patient_queues")
    }
    with op.batch_alter_table("patient_queues") as batch_op:
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

    indexes = {
        index["name"]
        for index in inspect(op.get_bind()).get_indexes("patient_queues")
        if index.get("name")
    }
    if "uq_patient_queues_facility_idempotency" not in indexes:
        op.create_index(
            "uq_patient_queues_facility_idempotency",
            "patient_queues",
            ["facility_slug", "idempotency_key"],
            unique=True,
        )
    if "uq_patient_queues_active_patient" not in indexes:
        op.create_index(
            "uq_patient_queues_active_patient",
            "patient_queues",
            ["facility_slug", "patient_id"],
            unique=True,
            postgresql_where=sa.text("status IN ('waiting', 'in_progress')"),
            sqlite_where=sa.text("status IN ('waiting', 'in_progress')"),
        )


def downgrade():
    indexes = {
        index["name"]
        for index in inspect(op.get_bind()).get_indexes("patient_queues")
        if index.get("name")
    }
    for index_name in (
        "uq_patient_queues_active_patient",
        "uq_patient_queues_facility_idempotency",
    ):
        if index_name in indexes:
            op.drop_index(index_name, table_name="patient_queues")
    columns = {
        column["name"]
        for column in inspect(op.get_bind()).get_columns("patient_queues")
    }
    with op.batch_alter_table("patient_queues") as batch_op:
        if "idempotency_payload_hash" in columns:
            batch_op.drop_column("idempotency_payload_hash")
        if "idempotency_key" in columns:
            batch_op.drop_column("idempotency_key")
