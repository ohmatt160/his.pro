import argparse
import statistics
import time

from sqlalchemy import text

from app.extensions import engine


QUERIES = {
    "patients": """
        SELECT id, first_name, last_name, email, created_at
        FROM patients
        WHERE facility_slug = :facility_slug
        ORDER BY created_at DESC
        LIMIT :limit
    """,
    "appointments": """
        SELECT id, patient_id, doctor_id, status, appointment_date
        FROM appointments
        WHERE facility_slug = :facility_slug
        ORDER BY appointment_date DESC
        LIMIT :limit
    """,
    "lab_orders": """
        SELECT id, patient_id, test_id, status, order_date
        FROM lab_orders
        WHERE facility_slug = :facility_slug
        ORDER BY order_date DESC
        LIMIT :limit
    """,
    "invoices": """
        SELECT id, patient_id, invoice_number, status, invoice_date
        FROM invoices
        WHERE facility_slug = :facility_slug
        ORDER BY invoice_date DESC
        LIMIT :limit
    """,
}


def measure(query_name: str, facility_slug: str, limit: int, runs: int) -> dict:
    statement = text(QUERIES[query_name])
    timings = []
    row_count = 0
    with engine.connect() as conn:
        for _ in range(runs):
            start = time.perf_counter()
            rows = conn.execute(
                statement,
                {"facility_slug": facility_slug, "limit": limit},
            ).fetchall()
            timings.append((time.perf_counter() - start) * 1000)
            row_count = len(rows)
    return {
        "query": query_name,
        "rows": row_count,
        "min_ms": round(min(timings), 2),
        "median_ms": round(statistics.median(timings), 2),
        "max_ms": round(max(timings), 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure common HIS.Pro list query latency.")
    parser.add_argument("--facility", required=True, help="Facility slug to test")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()

    for query_name in QUERIES:
        result = measure(query_name, args.facility, args.limit, args.runs)
        print(
            f"{result['query']}: rows={result['rows']} "
            f"min={result['min_ms']}ms median={result['median_ms']}ms max={result['max_ms']}ms"
        )


if __name__ == "__main__":
    main()
