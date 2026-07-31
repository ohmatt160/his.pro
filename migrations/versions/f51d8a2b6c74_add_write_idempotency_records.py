"""add durable write idempotency records

Revision ID: f51d8a2b6c74
Revises: e40c2d8f1a53
"""

from alembic import op
import sqlalchemy as sa


revision = "f51d8a2b6c74"
down_revision = "e40c2d8f1a53"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _index_names(table_name: str) -> set[str]:
    if table_name not in _table_names():
        return set()
    return {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes(table_name)
        if index.get("name")
    }


def _create_index_if_missing(name: str, table_name: str, columns, **kwargs) -> None:
    if table_name not in _table_names() or name in _index_names(table_name):
        return
    op.create_index(name, table_name, columns, **kwargs)


def upgrade():
    if "write_idempotency_records" not in _table_names():
        op.create_table(
            "write_idempotency_records",
            sa.Column("facility_id", sa.String(length=36), nullable=True),
            sa.Column("facility_slug", sa.String(length=100), nullable=False),
            sa.Column("actor_id", sa.String(length=36), nullable=True),
            sa.Column("operation", sa.String(length=120), nullable=False),
            sa.Column("idempotency_key", sa.String(length=200), nullable=False),
            sa.Column("payload_hash", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("resource_type", sa.String(length=80), nullable=True),
            sa.Column("resource_id", sa.String(length=36), nullable=True),
            sa.Column("resource_ids", sa.JSON(), nullable=True),
            sa.Column("response_status", sa.Integer(), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
            sa.ForeignKeyConstraint(["facility_slug"], ["facilities.slug"]),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(
        "ix_write_idempotency_records_actor_id",
        "write_idempotency_records",
        ["actor_id"],
    )
    _create_index_if_missing(
        "ix_write_idempotency_records_created_at",
        "write_idempotency_records",
        ["created_at"],
    )
    _create_index_if_missing(
        "ix_write_idempotency_records_facility_id",
        "write_idempotency_records",
        ["facility_id"],
    )
    _create_index_if_missing(
        "ix_write_idempotency_records_facility_slug",
        "write_idempotency_records",
        ["facility_slug"],
    )
    _create_index_if_missing(
        "ix_write_idempotency_records_resource_id",
        "write_idempotency_records",
        ["resource_id"],
    )
    _create_index_if_missing(
        "ix_write_idempotency_records_status",
        "write_idempotency_records",
        ["status"],
    )
    _create_index_if_missing(
        "idx_write_idempotency_facility_created",
        "write_idempotency_records",
        ["facility_slug", "created_at"],
    )
    _create_index_if_missing(
        "uq_write_idempotency_facility_operation_key",
        "write_idempotency_records",
        ["facility_slug", "operation", "idempotency_key"],
        unique=True,
    )
    _create_index_if_missing(
        "uq_inventory_active_facility_sku",
        "inventory",
        ["facility_slug", "sku"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
        sqlite_where=sa.text("is_active = 1"),
    )
    _create_index_if_missing(
        "uq_ward_beds_facility_ward_bed",
        "ward_beds",
        ["facility_slug", "ward_name", "bed_number"],
        unique=True,
    )
    _create_index_if_missing(
        "uq_ward_admissions_active_patient",
        "ward_admissions",
        ["facility_slug", "patient_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
        sqlite_where=sa.text("status = 'ACTIVE'"),
    )
    _create_index_if_missing(
        "uq_ward_admissions_active_bed",
        "ward_admissions",
        ["facility_slug", "bed_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE' AND bed_id IS NOT NULL"),
        sqlite_where=sa.text("status = 'ACTIVE' AND bed_id IS NOT NULL"),
    )
    _create_index_if_missing(
        "uq_suppliers_active_facility_name",
        "suppliers",
        ["facility_slug", "name"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
        sqlite_where=sa.text("is_active = 1"),
    )


def downgrade():
    op.drop_index("uq_suppliers_active_facility_name", table_name="suppliers")
    op.drop_index("uq_ward_admissions_active_bed", table_name="ward_admissions")
    op.drop_index("uq_ward_admissions_active_patient", table_name="ward_admissions")
    op.drop_index("uq_ward_beds_facility_ward_bed", table_name="ward_beds")
    op.drop_index("uq_inventory_active_facility_sku", table_name="inventory")
    op.drop_table("write_idempotency_records")
