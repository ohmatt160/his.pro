"""Bootstrap fresh or legacy databases, then apply Alembic migrations."""

import subprocess
import sys
import os
from pathlib import Path

from sqlalchemy import inspect

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.models  # noqa: F401
from app.extensions import Base, engine
from app.utils.schema import ensure_database_schema_current


BASELINE_REVISION = "6a2d8f7c9b10"
ALEMBIC_COMMAND = ["alembic", "-c", "migrations/alembic.ini"]


def run_alembic(*args: str) -> None:
    environment = os.environ.copy()
    existing_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        f"{ROOT_DIR}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(ROOT_DIR)
    )
    subprocess.run(
        [*ALEMBIC_COMMAND, *args],
        check=True,
        cwd=ROOT_DIR,
        env=environment,
    )


def main() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    if not existing_tables:
        # A real empty database must follow the full migration history. Tables
        # that predate Alembic coverage are added from metadata afterwards.
        run_alembic("upgrade", "head")
    elif "alembic_version" not in existing_tables:
        required_legacy_tables = {"facilities", "users"}
        missing = required_legacy_tables - existing_tables
        if missing:
            raise RuntimeError(
                "Refusing to stamp an unknown database as the HIS.Pro legacy "
                f"baseline; missing tables: {', '.join(sorted(missing))}"
            )
        run_alembic("stamp", BASELINE_REVISION)
        run_alembic("upgrade", "head")
    else:
        run_alembic("upgrade", "head")

    # Some early modules were introduced with create_all() before they had an
    # Alembic revision. This is additive only and runs after migrations so it
    # cannot pre-create tables owned by newer revisions.
    Base.metadata.create_all(bind=engine)
    ensure_database_schema_current(engine)


if __name__ == "__main__":
    main()
