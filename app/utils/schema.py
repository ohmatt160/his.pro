"""
Database schema compatibility helpers.

SQLAlchemy's create_all() creates missing tables, but it does not add columns to
tables that already exist. During development and early production deploys that
can leave databases behind the current models. This module applies conservative
additive repairs so startup reflects the model shape without destructive schema
changes.
"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.schema import CreateColumn

from app.extensions import Base
from app.utils.tenant_urls import generate_canonical_subdomain

logger = logging.getLogger(__name__)


def ensure_facility_canonical_subdomains(engine: Engine) -> None:
    """Backfill the immutable facility hostname on legacy development schemas."""
    if engine.dialect.name not in {"sqlite", "postgresql"}:
        return

    inspector = inspect(engine)
    if "facilities" not in set(inspector.get_table_names()):
        return

    columns = {column["name"] for column in inspector.get_columns("facilities")}
    with engine.begin() as connection:
        if "canonical_subdomain" not in columns:
            connection.execute(
                text(
                    'ALTER TABLE "facilities" '
                    'ADD COLUMN "canonical_subdomain" VARCHAR(63)'
                )
            )

        rows = connection.execute(
            text(
                'SELECT "id", "slug", "canonical_subdomain" '
                'FROM "facilities"'
            )
        ).mappings()
        for row in rows:
            if row["canonical_subdomain"]:
                continue
            connection.execute(
                text(
                    'UPDATE "facilities" '
                    'SET "canonical_subdomain" = :canonical_subdomain '
                    'WHERE "id" = :facility_id'
                ),
                {
                    "canonical_subdomain": generate_canonical_subdomain(
                        row["slug"],
                        row["id"],
                    ),
                    "facility_id": row["id"],
                },
            )

        connection.execute(
            text(
                'CREATE UNIQUE INDEX IF NOT EXISTS '
                '"ix_facilities_canonical_subdomain" '
                'ON "facilities" ("canonical_subdomain")'
            )
        )
        if engine.dialect.name == "postgresql":
            connection.execute(
                text(
                    'ALTER TABLE "facilities" '
                    'ALTER COLUMN "canonical_subdomain" SET NOT NULL'
                )
            )


def ensure_patient_registration_idempotency_index(engine: Engine) -> None:
    """Restore the patient-create uniqueness guard on additive legacy schemas."""
    if engine.dialect.name not in {"sqlite", "postgresql"}:
        return

    inspector = inspect(engine)
    if "patients" not in set(inspector.get_table_names()):
        return

    columns = {column["name"] for column in inspector.get_columns("patients")}
    if not {
        "facility_slug",
        "registration_idempotency_key",
    }.issubset(columns):
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                'CREATE UNIQUE INDEX IF NOT EXISTS '
                '"uq_patients_facility_registration_idempotency" '
                'ON "patients" ("facility_slug", "registration_idempotency_key")'
            )
        )


def ensure_billing_idempotency_indexes(engine: Engine) -> None:
    """Restore financial write uniqueness guards on additive legacy schemas."""
    if engine.dialect.name not in {"sqlite", "postgresql"}:
        return

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    index_specs = (
        (
            "invoices",
            {"facility_slug", "idempotency_key"},
            'CREATE UNIQUE INDEX IF NOT EXISTS '
            '"uq_invoices_facility_idempotency" '
            'ON "invoices" ("facility_slug", "idempotency_key")',
        ),
        (
            "payments",
            {"invoice_id", "idempotency_key"},
            'CREATE UNIQUE INDEX IF NOT EXISTS '
            '"uq_payments_invoice_idempotency" '
            'ON "payments" ("invoice_id", "idempotency_key")',
        ),
    )

    with engine.begin() as connection:
        for table_name, required_columns, statement in index_specs:
            if table_name not in tables:
                continue
            columns = {
                column["name"]
                for column in inspect(engine).get_columns(table_name)
            }
            if required_columns.issubset(columns):
                connection.execute(text(statement))


def ensure_clinical_idempotency_indexes(engine: Engine) -> None:
    """Restore duplicate-write guards on additive legacy schemas."""
    if engine.dialect.name not in {"sqlite", "postgresql"}:
        return

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    specs = (
        ("appointments", "uq_appointments_facility_idempotency"),
        ("medical_records", "uq_medical_records_facility_idempotency"),
        ("lab_orders", "uq_lab_orders_facility_idempotency"),
        ("prescriptions", "uq_prescriptions_facility_idempotency"),
        ("patient_queues", "uq_patient_queues_facility_idempotency"),
    )
    with engine.begin() as connection:
        for table_name, index_name in specs:
            if table_name not in tables:
                continue
            columns = {
                column["name"]
                for column in inspect(engine).get_columns(table_name)
            }
            if {"facility_slug", "idempotency_key"}.issubset(columns):
                connection.execute(
                    text(
                        f'CREATE UNIQUE INDEX IF NOT EXISTS "{index_name}" '
                        f'ON "{table_name}" ("facility_slug", "idempotency_key")'
                    )
                )


def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _can_add_column(column) -> bool:
    if column.primary_key:
        return False

    if not column.nullable and column.default is None and column.server_default is None:
        return False

    return True


def _compile_column(column, engine: Engine) -> str:
    return str(CreateColumn(column).compile(dialect=engine.dialect))


def ensure_sqlite_schema_current(engine: Engine) -> None:
    """
    Add missing model columns to existing SQLite tables.

    This is intentionally conservative: it only touches SQLite, only adds
    missing columns, and skips columns SQLite cannot safely add to populated
    tables. Destructive changes and type changes should still be handled through
    explicit migrations.
    """
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    planned_updates: list[tuple[str, str, str]] = []

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue

        existing_columns = {
            column["name"] for column in inspector.get_columns(table.name)
        }

        for column in table.columns:
            if column.name in existing_columns:
                continue

            if not _can_add_column(column):
                logger.warning(
                    "Skipping automatic schema sync for %s.%s; column is not "
                    "safe to add automatically.",
                    table.name,
                    column.name,
                )
                continue

            planned_updates.append(
                (
                    table.name,
                    column.name,
                    f"ALTER TABLE {_quote_identifier(table.name)} "
                    f"ADD COLUMN {_compile_column(column, engine)}",
                )
            )

    if not planned_updates:
        return

    with engine.begin() as connection:
        for table_name, column_name, statement in planned_updates:
            logger.info("Adding missing SQLite column %s.%s", table_name, column_name)
            connection.execute(text(statement))


def ensure_postgresql_additive_schema_current(engine: Engine) -> None:
    """
    Add missing nullable/defaulted model columns to existing PostgreSQL tables.

    This is intentionally additive only. It does not drop columns, rename
    columns, change constraints, or rewrite data. It is here to keep small
    hosted deployments from breaking when a new model column is introduced
    before a full migration system is in place.
    """
    if engine.dialect.name != "postgresql":
        return

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    planned_updates: list[tuple[str, str, str]] = []

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue

        existing_columns = {
            column["name"] for column in inspector.get_columns(table.name)
        }

        for column in table.columns:
            if column.name in existing_columns:
                continue

            if not _can_add_column(column):
                logger.warning(
                    "Skipping automatic PostgreSQL schema sync for %s.%s; "
                    "column is not safe to add automatically.",
                    table.name,
                    column.name,
                )
                continue

            planned_updates.append(
                (
                    table.name,
                    column.name,
                    f"ALTER TABLE {_quote_identifier(table.name)} "
                    f"ADD COLUMN {_compile_column(column, engine)}",
                )
            )

    if not planned_updates:
        return

    with engine.begin() as connection:
        for table_name, column_name, statement in planned_updates:
            logger.info("Adding missing PostgreSQL column %s.%s", table_name, column_name)
            connection.execute(text(statement))


def ensure_database_schema_current(engine: Engine) -> None:
    """
    Apply conservative startup schema compatibility repairs.

    SQLite and PostgreSQL receive additive column updates. PostgreSQL also gets
    safe widening fixes for columns that older deployments created too narrowly.
    """
    ensure_facility_canonical_subdomains(engine)
    ensure_sqlite_schema_current(engine)

    if engine.dialect.name == "postgresql":
        ensure_postgresql_additive_schema_current(engine)

    ensure_patient_registration_idempotency_index(engine)
    ensure_billing_idempotency_indexes(engine)
    ensure_clinical_idempotency_indexes(engine)

    if engine.dialect.name != "postgresql":
        return

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    if "users" not in existing_tables:
        return

    users_columns = {column["name"]: column for column in inspector.get_columns("users")}
    password_hash = users_columns.get("password_hash")
    if not password_hash:
        return

    current_length = getattr(password_hash["type"], "length", None)
    if current_length is not None and current_length >= 255:
        return

    with engine.begin() as connection:
        logger.info("Widening users.password_hash to VARCHAR(255)")
        connection.execute(
            text("ALTER TABLE users ALTER COLUMN password_hash TYPE VARCHAR(255)")
        )
