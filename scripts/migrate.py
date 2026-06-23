"""Bootstrap legacy databases once, then apply Alembic migrations normally."""

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

    if "alembic_version" not in existing_tables:
        Base.metadata.create_all(bind=engine)
        ensure_database_schema_current(engine)
        run_alembic("stamp", BASELINE_REVISION)

    run_alembic("upgrade", "head")


if __name__ == "__main__":
    main()
