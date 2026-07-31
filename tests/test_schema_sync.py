import unittest
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

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
                    INSERT INTO facilities (id, name, type, slug)
                    VALUES ('facility-1', 'API Clinic', 'clinic', 'api')
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE TABLE patients (
                        id VARCHAR(36) PRIMARY KEY,
                        created_at DATETIME,
                        updated_at DATETIME,
                        first_name VARCHAR(100) NOT NULL,
                        last_name VARCHAR(100) NOT NULL,
                        date_of_birth DATE NOT NULL,
                        facility_slug VARCHAR(100)
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
            connection.execute(
                text(
                    """
                    CREATE TABLE invoices (
                        id VARCHAR(36) PRIMARY KEY,
                        created_at DATETIME,
                        updated_at DATETIME,
                        patient_id VARCHAR(36) NOT NULL,
                        invoice_number VARCHAR(50) UNIQUE NOT NULL,
                        facility_slug VARCHAR(100),
                        status VARCHAR(50),
                        subtotal NUMERIC(10, 2),
                        tax NUMERIC(10, 2),
                        discount NUMERIC(10, 2),
                        total NUMERIC(10, 2),
                        notes TEXT,
                        due_date DATE,
                        invoice_date DATETIME NOT NULL,
                        paid_date DATETIME
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE TABLE lab_orders (
                        id VARCHAR(36) PRIMARY KEY,
                        created_at DATETIME,
                        updated_at DATETIME,
                        patient_id VARCHAR(36) NOT NULL,
                        test_id VARCHAR(36) NOT NULL,
                        facility_slug VARCHAR(100),
                        ordered_by VARCHAR(36),
                        performed_by VARCHAR(36),
                        status VARCHAR(50),
                        priority VARCHAR(20),
                        notes TEXT,
                        order_date DATETIME NOT NULL,
                        collection_date DATETIME,
                        completed_date DATETIME
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE TABLE payments (
                        id VARCHAR(36) PRIMARY KEY,
                        created_at DATETIME,
                        updated_at DATETIME,
                        invoice_id VARCHAR(36) NOT NULL,
                        amount NUMERIC(10, 2) NOT NULL,
                        payment_method VARCHAR(50),
                        payment_date DATETIME NOT NULL
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE TABLE radiology_orders (
                        id VARCHAR(36) PRIMARY KEY,
                        created_at DATETIME,
                        updated_at DATETIME,
                        patient_id VARCHAR(36) NOT NULL,
                        facility_slug VARCHAR(100) NOT NULL,
                        request_date DATETIME,
                        modality VARCHAR(50) NOT NULL,
                        body_part VARCHAR(100) NOT NULL,
                        clinical_notes TEXT,
                        status VARCHAR(50),
                        requested_by VARCHAR(36) NOT NULL,
                        radiologist_id VARCHAR(36),
                        report TEXT,
                        report_date DATETIME
                    )
                    """
                )
            )

        ensure_database_schema_current(engine)

        inspector = inspect(engine)
        facility_columns = {column["name"] for column in inspector.get_columns("facilities")}
        patient_columns = {column["name"] for column in inspector.get_columns("patients")}
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        audit_columns = {column["name"] for column in inspector.get_columns("audit_logs")}
        invoice_columns = {column["name"] for column in inspector.get_columns("invoices")}
        payment_columns = {column["name"] for column in inspector.get_columns("payments")}
        lab_order_columns = {column["name"] for column in inspector.get_columns("lab_orders")}
        radiology_order_columns = {column["name"] for column in inspector.get_columns("radiology_orders")}

        self.assertIn("canonical_subdomain", facility_columns)
        with engine.connect() as connection:
            canonical_subdomain = connection.execute(
                text(
                    "SELECT canonical_subdomain FROM facilities "
                    "WHERE id = 'facility-1'"
                )
            ).scalar_one()
        self.assertNotEqual(canonical_subdomain, "api")
        self.assertLessEqual(len(canonical_subdomain), 63)
        self.assertIn(
            "ix_facilities_canonical_subdomain",
            {index["name"] for index in inspector.get_indexes("facilities")},
        )
        self.assertIn("registration_idempotency_key", patient_columns)
        self.assertIn("registration_payload_hash", patient_columns)
        self.assertIn(
            "uq_patients_facility_registration_idempotency",
            {index["name"] for index in inspector.get_indexes("patients")},
        )
        self.assertIn("facility_id", user_columns)
        self.assertIn("must_change_password", user_columns)
        self.assertIn("last_password_change", user_columns)
        self.assertIn("facility_id", audit_columns)
        self.assertIn("ip_address", audit_columns)
        self.assertIn("user_agent", audit_columns)
        self.assertIn("branch_id", invoice_columns)
        self.assertIn("department_id", invoice_columns)
        self.assertIn("idempotency_key", invoice_columns)
        self.assertIn("idempotency_payload_hash", invoice_columns)
        self.assertIn(
            "uq_invoices_facility_idempotency",
            {index["name"] for index in inspector.get_indexes("invoices")},
        )
        self.assertIn("idempotency_key", payment_columns)
        self.assertIn("idempotency_payload_hash", payment_columns)
        self.assertIn(
            "uq_payments_invoice_idempotency",
            {index["name"] for index in inspector.get_indexes("payments")},
        )
        self.assertIn("branch_id", lab_order_columns)
        self.assertIn("department_id", lab_order_columns)
        self.assertIn("branch_id", radiology_order_columns)
        self.assertIn("department_id", radiology_order_columns)


if __name__ == "__main__":
    unittest.main()
