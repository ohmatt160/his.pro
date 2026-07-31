"""enforce pharmacy and lab invariants

Revision ID: e40c2d8f1a53
Revises: d39b1c7e0f42
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "e40c2d8f1a53"
down_revision = "d39b1c7e0f42"
branch_labels = None
depends_on = None


def _assert_no_duplicates(table_name: str, column_name: str) -> None:
    duplicate = op.get_bind().execute(
        sa.text(
            f'SELECT "{column_name}" FROM "{table_name}" '
            f'GROUP BY "{column_name}" HAVING COUNT(*) > 1 LIMIT 1'
        )
    ).scalar()
    if duplicate is not None:
        raise RuntimeError(
            f"{table_name} contains duplicate {column_name} values; "
            "resolve them before applying this migration"
        )


def upgrade():
    specs = (
        ("pharmacy_inventory", "medication_id", "uq_pharmacy_inventory_medication"),
        ("lab_results", "order_id", "uq_lab_results_order"),
    )
    for table_name, column_name, index_name in specs:
        _assert_no_duplicates(table_name, column_name)
        indexes = {
            index["name"]
            for index in inspect(op.get_bind()).get_indexes(table_name)
            if index.get("name")
        }
        if index_name not in indexes:
            op.create_index(
                index_name,
                table_name,
                [column_name],
                unique=True,
            )


def downgrade():
    for table_name, index_name in (
        ("lab_results", "uq_lab_results_order"),
        ("pharmacy_inventory", "uq_pharmacy_inventory_medication"),
    ):
        indexes = {
            index["name"]
            for index in inspect(op.get_bind()).get_indexes(table_name)
            if index.get("name")
        }
        if index_name in indexes:
            op.drop_index(index_name, table_name=table_name)
