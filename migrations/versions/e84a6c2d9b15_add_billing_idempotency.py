"""add billing idempotency

Revision ID: e84a6c2d9b15
Revises: d73f8b1a2c44
"""

from alembic import op
import sqlalchemy as sa


revision = "e84a6c2d9b15"
down_revision = "d73f8b1a2c44"
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


def _add_columns_if_missing(table_name: str) -> None:
    columns = _column_names(table_name)
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


def upgrade():
    _add_columns_if_missing("invoices")
    _add_columns_if_missing("payments")

    if "uq_invoices_facility_idempotency" not in _index_names("invoices"):
        op.create_index(
            "uq_invoices_facility_idempotency",
            "invoices",
            ["facility_slug", "idempotency_key"],
            unique=True,
        )
    if "uq_payments_invoice_idempotency" not in _index_names("payments"):
        op.create_index(
            "uq_payments_invoice_idempotency",
            "payments",
            ["invoice_id", "idempotency_key"],
            unique=True,
        )


def downgrade():
    if "uq_payments_invoice_idempotency" in _index_names("payments"):
        op.drop_index("uq_payments_invoice_idempotency", table_name="payments")
    if "uq_invoices_facility_idempotency" in _index_names("invoices"):
        op.drop_index("uq_invoices_facility_idempotency", table_name="invoices")

    with op.batch_alter_table("payments") as batch_op:
        columns = _column_names("payments")
        if "idempotency_payload_hash" in columns:
            batch_op.drop_column("idempotency_payload_hash")
        if "idempotency_key" in columns:
            batch_op.drop_column("idempotency_key")

    with op.batch_alter_table("invoices") as batch_op:
        columns = _column_names("invoices")
        if "idempotency_payload_hash" in columns:
            batch_op.drop_column("idempotency_payload_hash")
        if "idempotency_key" in columns:
            batch_op.drop_column("idempotency_key")
