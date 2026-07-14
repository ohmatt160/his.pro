import os
import sys
import tempfile
import unittest
import asyncio
import io
import json
from datetime import date
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tests.test_app_factory import import_isolated_app


class DataMigrationServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.database_path = os.path.join(cls.temp_dir.name, "data-migration.db")
        os.environ["DATABASE_URL"] = f"sqlite:///{cls.database_path}"
        os.environ["RATE_LIMIT_NAMESPACE"] = f"data-migration-{os.path.basename(cls.temp_dir.name)}"

        app, Base, db_session, engine, httpx = import_isolated_app()
        Base.metadata.create_all(bind=engine)
        cls.db_session = db_session
        cls.engine = engine

        from app.models.facility import Facility
        from app.models.user import User

        cls.Facility = Facility
        cls.User = User

    @classmethod
    def tearDownClass(cls):
        cls.db_session.remove()
        cls.engine.dispose()
        cls.temp_dir.cleanup()

    def setUp(self):
        from app.models.audit_log import AuditLog
        from app.models.appointment import Appointment
        from app.models.inventory import Inventory
        from app.models.patient import Patient

        self.db_session.query(AuditLog).delete()
        self.db_session.query(Appointment).delete()
        self.db_session.query(Inventory).delete()
        self.db_session.query(Patient).delete()
        self.db_session.query(self.User).delete()
        self.db_session.query(self.Facility).delete()
        self.db_session.commit()

        self.alpha = self.Facility(
            name="Alpha Hospital",
            slug="alpha-hospital",
            type="hospital",
            is_active=True,
        )
        self.beta = self.Facility(
            name="Beta Hospital",
            slug="beta-hospital",
            type="hospital",
            is_active=True,
        )
        self.admin = self.User(
            username="alpha-admin",
            email="alpha-admin@example.com",
            role="ADMIN",
            first_name="Alpha",
            last_name="Admin",
            facility_slug="alpha-hospital",
        )
        self.admin.set_password("AdminPass2026")
        self.doctor = self.User(
            username="alpha-doctor",
            email="alpha-doctor@example.com",
            role="DOCTOR",
            first_name="Alpha",
            last_name="Doctor",
            facility_slug="alpha-hospital",
        )
        self.doctor.set_password("DoctorPass2026")
        self.db_session.add_all([self.alpha, self.beta, self.admin, self.doctor])
        self.db_session.commit()

    def _parsed(self, import_mode, rows_by_entity):
        from app.services.data_migration_service import ParsedMigration

        return ParsedMigration(
            source_system="generic_csv",
            import_mode=import_mode,
            file_name="migration.csv",
            file_size=100,
            detected_format="csv",
            rows_by_entity=rows_by_entity,
            warnings=[],
        )

    def test_patient_import_is_scoped_to_facility_and_skips_same_tenant_duplicates(self):
        from app.models.patient import Patient
        from app.services.data_migration_service import DataMigrationService

        beta_patient = Patient(
            first_name="Jane",
            last_name="Tenant",
            date_of_birth=date(1990, 1, 1),
            email="jane@example.com",
            facility_slug="beta-hospital",
            is_active=True,
        )
        self.db_session.add(beta_patient)
        self.db_session.commit()

        parsed = self._parsed("patients", {
            "patients": [
                {
                    "first_name": "Jane",
                    "last_name": "Tenant",
                    "date_of_birth": "1990-01-01",
                    "email": "jane@example.com",
                },
                {
                    "first_name": "Jane",
                    "last_name": "Tenant",
                    "date_of_birth": "1990-01-01",
                    "email": "jane@example.com",
                },
            ]
        })
        result = DataMigrationService.import_parsed(parsed, self.db_session, self.alpha, self.admin)
        self.db_session.commit()

        self.assertEqual(result["imported"]["patients"], 1)
        self.assertEqual(result["skipped_duplicates"]["patients"], 1)
        self.assertEqual(
            self.db_session.query(Patient).filter_by(facility_slug="alpha-hospital").count(),
            1,
        )
        self.assertEqual(
            self.db_session.query(Patient).filter_by(facility_slug="beta-hospital").count(),
            1,
        )

    def test_inventory_staff_and_appointments_import_with_duplicate_safety(self):
        from app.models.appointment import Appointment
        from app.models.inventory import Inventory
        from app.models.patient import Patient
        from app.services.data_migration_service import DataMigrationService

        patient = Patient(
            first_name="Appt",
            last_name="Patient",
            date_of_birth=date(1985, 2, 3),
            email="appt.patient@example.com",
            facility_slug="alpha-hospital",
            is_active=True,
        )
        self.db_session.add(patient)
        self.db_session.commit()

        parsed = self._parsed("full_archive", {
            "inventory": [
                {"sku": "GLOVE-001", "name": "Sterile Gloves", "category": "supplies", "unit": "box"},
                {"sku": "GLOVE-001", "name": "Sterile Gloves", "category": "supplies", "unit": "box"},
            ],
            "staff": [
                {
                    "username": "new-nurse",
                    "email": "new-nurse@example.com",
                    "first_name": "New",
                    "last_name": "Nurse",
                    "role": "nurse",
                }
            ],
            "appointments": [
                {
                    "patient_email": "appt.patient@example.com",
                    "doctor_username": "alpha-doctor",
                    "appointment_date": "2026-08-01 09:30",
                    "reason": "Migration check",
                }
            ],
        })
        result = DataMigrationService.import_parsed(parsed, self.db_session, self.alpha, self.admin)
        self.db_session.commit()

        self.assertEqual(result["imported"]["inventory"], 1)
        self.assertEqual(result["skipped_duplicates"]["inventory"], 1)
        self.assertEqual(result["imported"]["staff"], 1)
        self.assertEqual(result["imported"]["appointments"], 1)
        self.assertEqual(self.db_session.query(Inventory).filter_by(facility_slug="alpha-hospital").count(), 1)
        self.assertEqual(self.db_session.query(self.User).filter_by(username="new-nurse").count(), 1)
        self.assertEqual(self.db_session.query(Appointment).filter_by(facility_slug="alpha-hospital").count(), 1)

    def test_openmrs_nested_patient_export_is_mapped_safely(self):
        from fastapi import UploadFile
        from app.models.patient import Patient
        from app.services.data_migration_service import DataMigrationService

        payload = {
            "results": [
                {
                    "person": {
                        "names": [{"givenName": "Open", "familyName": "Mrs", "preferred": True}],
                        "gender": "F",
                        "birthdate": "1992-04-05",
                        "attributes": [
                            {"displayName": "Telephone Number", "value": "+234800000101"},
                            {"displayName": "Email Address", "value": "openmrs.patient@example.com"},
                        ],
                    },
                    "identifiers": [{"identifier": "OMRS-001"}],
                }
            ]
        }
        upload = UploadFile(
            filename="openmrs.json",
            file=io.BytesIO(json.dumps(payload).encode("utf-8")),
        )
        parsed = asyncio.run(DataMigrationService.parse_upload(upload, "openmrs", "patients"))
        result = DataMigrationService.import_parsed(parsed, self.db_session, self.alpha, self.admin)
        self.db_session.commit()

        self.assertEqual(result["imported"]["patients"], 1)
        patient = self.db_session.query(Patient).filter_by(email="openmrs.patient@example.com").first()
        self.assertIsNotNone(patient)
        self.assertEqual(patient.first_name, "Open")
        self.assertEqual(patient.last_name, "Mrs")
        self.assertEqual(patient.gender, "FEMALE")

    def test_dhis2_tracked_entity_attributes_are_mapped(self):
        from fastapi import UploadFile
        from app.models.patient import Patient
        from app.services.data_migration_service import DataMigrationService

        payload = {
            "trackedEntityInstances": [
                {
                    "trackedEntityInstance": "TEI123",
                    "attributes": [
                        {"displayName": "First Name", "value": "Dhis"},
                        {"displayName": "Surname", "value": "Two"},
                        {"displayName": "Date of Birth", "value": "1994-06-07"},
                        {"displayName": "Phone Number", "value": "+234800000202"},
                    ],
                }
            ]
        }
        upload = UploadFile(
            filename="dhis2.json",
            file=io.BytesIO(json.dumps(payload).encode("utf-8")),
        )
        parsed = asyncio.run(DataMigrationService.parse_upload(upload, "dhis2", "patients"))
        result = DataMigrationService.import_parsed(parsed, self.db_session, self.alpha, self.admin)
        self.db_session.commit()

        self.assertEqual(result["imported"]["patients"], 1)
        patient = self.db_session.query(Patient).filter_by(phone="+234800000202").first()
        self.assertIsNotNone(patient)
        self.assertEqual(patient.first_name, "Dhis")
        self.assertEqual(patient.last_name, "Two")
