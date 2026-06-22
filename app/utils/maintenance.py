import logging
import time
from contextlib import contextmanager

from sqlalchemy import text

from app.extensions import engine
logger = logging.getLogger(__name__)


@contextmanager
def _transaction():
    with engine.begin() as conn:
        yield conn


def run_maintenance() -> None:
    """Refresh PostgreSQL planner statistics after large imports or heavy churn."""
    with _transaction() as conn:
        conn.execute(text("ANALYZE"))
    logger.info("Database ANALYZE complete")


def vacuum_analyze() -> None:
    """Run VACUUM ANALYZE outside an explicit transaction."""
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("VACUUM ANALYZE"))
    logger.info("Database VACUUM ANALYZE complete")


def measure_patient_list_query(facility_slug: str, limit: int = 20) -> dict:
    start = time.perf_counter()
    with _transaction() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, first_name, last_name, email, created_at
                FROM patients
                WHERE facility_slug = :facility_slug
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"facility_slug": facility_slug, "limit": limit},
        ).fetchall()
    elapsed_ms = (time.perf_counter() - start) * 1000
    return {
        "query": "patients_by_facility",
        "facility_slug": facility_slug,
        "returned": len(rows),
        "elapsed_ms": round(elapsed_ms, 2),
    }


def explain_patient_list_query(facility_slug: str, limit: int = 20) -> list[str]:
    with _transaction() as conn:
        plan = conn.execute(
            text(
                """
                EXPLAIN (ANALYZE, BUFFERS)
                SELECT id, first_name, last_name, email, created_at
                FROM patients
                WHERE facility_slug = :facility_slug
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"facility_slug": facility_slug, "limit": limit},
        ).fetchall()
    return [row[0] for row in plan]
