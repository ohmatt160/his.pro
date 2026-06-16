import unittest

from sqlalchemy import create_engine, inspect, text

import app.models  # noqa: F401 - registers model tables on Base metadata
from app.utils.schema import ensure_database_schema_current


class SchemaSyncTest(unittest.TestCase):
    def test_sqlite_schema_sync_adds_missing_safe_columns(self):
        engine = create_engine("sqlite:///:memory:")

        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE facilities (
                        id VARCHAR(36) PRIMARY KEY,
                        created_at DATETIME,
                        updated_at DATETIME,
                        name VARCHAR(200) NOT NULL,
                        type VARCHAR(50) NOT NULL,
                        slug VARCHAR(100) UNIQUE NOT NULL
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE TABLE users (
                        id VARCHAR(36) PRIMARY KEY,
                        created_at DATETIME,
                        updated_at DATETIME,
                        username VARCHAR(80) UNIQUE NOT NULL,
                        email VARCHAR(120) UNIQUE NOT NULL,
                        password_hash VARCHAR(128) NOT NULL,
                        role VARCHAR(50) NOT NULL,
                        is_active BOOLEAN
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE TABLE audit_logs (
                        id VARCHAR(36) PRIMARY KEY,
                        created_at DATETIME,
                        updated_at DATETIME,
                        user_id VARCHAR(36),
                        action VARCHAR(100) NOT NULL,
                        resource_type VARCHAR(50),
                        resource_id VARCHAR(36),
                        facility_slug VARCHAR(100),
                        details JSON
                    )
                    """
                )
            )

        ensure_database_schema_current(engine)

        inspector = inspect(engine)
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        audit_columns = {column["name"] for column in inspector.get_columns("audit_logs")}

        self.assertIn("facility_id", user_columns)
        self.assertIn("must_change_password", user_columns)
        self.assertIn("last_password_change", user_columns)
        self.assertIn("facility_id", audit_columns)
        self.assertIn("ip_address", audit_columns)
        self.assertIn("user_agent", audit_columns)


if __name__ == "__main__":
    unittest.main()
