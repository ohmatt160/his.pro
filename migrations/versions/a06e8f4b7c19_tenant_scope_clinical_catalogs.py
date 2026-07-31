"""tenant scope clinical catalogs

Revision ID: a06e8f4b7c19
Revises: f95d7e3a0c26
"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "a06e8f4b7c19"
down_revision = "f95d7e3a0c26"
branch_labels = None
depends_on = None


NAMING_CONVENTION = {
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
}


def _columns(table_name: str) -> set[str]:
    return {
        column["name"]
        for column in inspect(op.get_bind()).get_columns(table_name)
    }


def _index_names(table_name: str) -> set[str]:
    return {
        index["name"]
        for index in inspect(op.get_bind()).get_indexes(table_name)
        if index.get("name")
    }


def _foreign_key_columns(table_name: str) -> set[tuple[str, ...]]:
    return {
        tuple(foreign_key.get("constrained_columns") or ())
        for foreign_key in inspect(op.get_bind()).get_foreign_keys(table_name)
    }


def _add_tenant_columns() -> None:
    lab_columns = _columns("lab_tests")
    lab_foreign_keys = _foreign_key_columns("lab_tests")
    with op.batch_alter_table(
        "lab_tests",
        naming_convention=NAMING_CONVENTION,
    ) as batch_op:
        if "facility_id" not in lab_columns:
            batch_op.add_column(sa.Column("facility_id", sa.String(length=36), nullable=True))
        if "facility_slug" not in lab_columns:
            batch_op.add_column(sa.Column("facility_slug", sa.String(length=100), nullable=True))
        if ("facility_id",) not in lab_foreign_keys:
            batch_op.create_foreign_key(
                "fk_lab_tests_facility_id_facilities",
                "facilities",
                ["facility_id"],
                ["id"],
            )
        if ("facility_slug",) not in lab_foreign_keys:
            batch_op.create_foreign_key(
                "fk_lab_tests_facility_slug_facilities",
                "facilities",
                ["facility_slug"],
                ["slug"],
            )

    medication_columns = _columns("medications")
    medication_foreign_keys = _foreign_key_columns("medications")
    with op.batch_alter_table(
        "medications",
        naming_convention=NAMING_CONVENTION,
    ) as batch_op:
        if "facility_id" not in medication_columns:
            batch_op.add_column(sa.Column("facility_id", sa.String(length=36), nullable=True))
        if ("facility_id",) not in medication_foreign_keys:
            batch_op.create_foreign_key(
                "fk_medications_facility_id_facilities",
                "facilities",
                ["facility_id"],
                ["id"],
            )


def _drop_global_code_uniqueness(table_name: str) -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    matching_constraints = [
        constraint
        for constraint in inspector.get_unique_constraints(table_name)
        if tuple(constraint.get("column_names") or ()) == ("code",)
    ]
    matching_indexes = [
        index
        for index in inspector.get_indexes(table_name)
        if index.get("unique")
        and tuple(index.get("column_names") or ()) == ("code",)
    ]

    if matching_constraints:
        with op.batch_alter_table(
            table_name,
            naming_convention=NAMING_CONVENTION,
        ) as batch_op:
            for constraint in matching_constraints:
                batch_op.drop_constraint(
                    constraint.get("name") or f"uq_{table_name}_code",
                    type_="unique",
                )

    for index in matching_indexes:
        if index.get("name"):
            op.drop_index(index["name"], table_name=table_name)


def _copy_lab_catalog_per_facility() -> None:
    bind = op.get_bind()
    facilities = list(
        bind.execute(
            sa.text('SELECT "id", "slug" FROM "facilities" ORDER BY "slug"')
        ).mappings()
    )
    if not facilities:
        return

    facilities_by_slug = {facility["slug"]: facility for facility in facilities}
    tests = list(
        bind.execute(
            sa.text(
                'SELECT "id", "name", "code", "description", "category", '
                '"unit", "reference_range", "price", "is_active", '
                '"created_at", "updated_at", "facility_id", "facility_slug" '
                'FROM "lab_tests" ORDER BY "created_at", "id"'
            )
        ).mappings()
    )

    for test in tests:
        usage_slugs = {
            row["facility_slug"]
            for row in bind.execute(
                sa.text(
                    'SELECT DISTINCT "facility_slug" FROM "lab_orders" '
                    'WHERE "test_id" = :test_id AND "facility_slug" IS NOT NULL'
                ),
                {"test_id": test["id"]},
            ).mappings()
            if row["facility_slug"] in facilities_by_slug
        }
        if test["facility_slug"] in facilities_by_slug:
            target_slugs = sorted(usage_slugs | {test["facility_slug"]})
            owner_slug = test["facility_slug"]
        else:
            # The legacy catalog was global. Copying it to every existing tenant
            # preserves availability while ending future cross-tenant mutation.
            target_slugs = sorted(facilities_by_slug)
            owner_slug = target_slugs[0]

        owner = facilities_by_slug[owner_slug]
        bind.execute(
            sa.text(
                'UPDATE "lab_tests" SET "facility_id" = :facility_id, '
                '"facility_slug" = :facility_slug WHERE "id" = :test_id'
            ),
            {
                "facility_id": owner["id"],
                "facility_slug": owner_slug,
                "test_id": test["id"],
            },
        )

        for facility_slug in target_slugs:
            if facility_slug == owner_slug:
                continue
            facility = facilities_by_slug[facility_slug]
            existing_id = bind.execute(
                sa.text(
                    'SELECT "id" FROM "lab_tests" '
                    'WHERE "facility_slug" = :facility_slug AND "code" = :code '
                    'LIMIT 1'
                ),
                {"facility_slug": facility_slug, "code": test["code"]},
            ).scalar()
            clone_id = existing_id or str(uuid.uuid4())
            if not existing_id:
                bind.execute(
                    sa.text(
                        'INSERT INTO "lab_tests" '
                        '("id", "name", "code", "description", "category", '
                        '"unit", "reference_range", "price", "is_active", '
                        '"created_at", "updated_at", "facility_id", "facility_slug") '
                        'VALUES (:id, :name, :code, :description, :category, '
                        ':unit, :reference_range, :price, :is_active, '
                        ':created_at, :updated_at, :facility_id, :facility_slug)'
                    ),
                    {
                        **dict(test),
                        "id": clone_id,
                        "facility_id": facility["id"],
                        "facility_slug": facility_slug,
                    },
                )
            bind.execute(
                sa.text(
                    'UPDATE "lab_orders" SET "test_id" = :clone_id '
                    'WHERE "test_id" = :test_id AND "facility_slug" = :facility_slug'
                ),
                {
                    "clone_id": clone_id,
                    "test_id": test["id"],
                    "facility_slug": facility_slug,
                },
            )


def _backfill_facility_ids() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            'UPDATE "lab_tests" SET "facility_id" = '
            '(SELECT "id" FROM "facilities" '
            ' WHERE "facilities"."slug" = "lab_tests"."facility_slug") '
            'WHERE "facility_slug" IS NOT NULL AND "facility_id" IS NULL'
        )
    )
    bind.execute(
        sa.text(
            'UPDATE "medications" SET "facility_id" = '
            '(SELECT "id" FROM "facilities" '
            ' WHERE "facilities"."slug" = "medications"."facility_slug") '
            'WHERE "facility_slug" IS NOT NULL AND "facility_id" IS NULL'
        )
    )


def _create_tenant_indexes() -> None:
    index_specs = (
        ("ix_lab_tests_facility_id", "lab_tests", ["facility_id"], False),
        ("ix_lab_tests_facility_slug", "lab_tests", ["facility_slug"], False),
        (
            "uq_lab_tests_facility_code",
            "lab_tests",
            ["facility_slug", "code"],
            True,
        ),
        (
            "idx_lab_tests_facility_active",
            "lab_tests",
            ["facility_slug", "is_active"],
            False,
        ),
        ("ix_medications_facility_id", "medications", ["facility_id"], False),
        (
            "uq_medications_facility_code",
            "medications",
            ["facility_slug", "code"],
            True,
        ),
    )
    for name, table_name, columns, unique in index_specs:
        if name not in _index_names(table_name):
            op.create_index(name, table_name, columns, unique=unique)


def upgrade():
    _add_tenant_columns()
    _drop_global_code_uniqueness("lab_tests")
    _drop_global_code_uniqueness("medications")
    _copy_lab_catalog_per_facility()
    _backfill_facility_ids()
    _create_tenant_indexes()


def downgrade():
    # A downgrade cannot safely restore global code uniqueness once two
    # facilities own the same code. Keep tenant data intact and remove only the
    # additive indexes/columns that do not risk deleting clinical references.
    for name, table_name in (
        ("uq_medications_facility_code", "medications"),
        ("ix_medications_facility_id", "medications"),
        ("idx_lab_tests_facility_active", "lab_tests"),
        ("uq_lab_tests_facility_code", "lab_tests"),
        ("ix_lab_tests_facility_slug", "lab_tests"),
        ("ix_lab_tests_facility_id", "lab_tests"),
    ):
        if name in _index_names(table_name):
            op.drop_index(name, table_name=table_name)
