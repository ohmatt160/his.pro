"""
Database schema compatibility helpers.

SQLAlchemy's create_all() creates missing tables, but it does not add columns to
tables that already exist. During local development that can leave SQLite
databases behind the current models. This module applies only additive, safe
column updates for SQLite so startup reflects the model shape without requiring
manual ALTER TABLE commands.
"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.schema import CreateColumn

from app.extensions import Base

logger = logging.getLogger(__name__)


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

