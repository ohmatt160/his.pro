import os
import sys
import tempfile
import unittest
import asyncio
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tests.test_app_factory import import_isolated_app


class TenantIsolationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.database_path = os.path.join(cls.temp_dir.name, "tenant-isolation.db")
        os.environ["DATABASE_URL"] = f"sqlite:///{cls.database_path}"
        os.environ["RATE_LIMIT_NAMESPACE"] = f"tenant-isolation-{os.path.basename(cls.temp_dir.name)}"
        os.environ["FILE_UPLOAD_DIR"] = os.path.join(cls.temp_dir.name, "uploads")
        os.environ["RECEIPT_UPLOAD_DIR"] = os.path.join(cls.temp_dir.name, "receipts")

        app, Base, db_session, engine, httpx = import_isolated_app()

        Base.metadata.create_all(bind=engine)
        cls.app = app
        cls.db_session = db_session
        cls.engine = engine
        cls.httpx = httpx

    @classmethod
    def tearDownClass(cls):
        cls.db_session.remove()
        cls.engine.dispose()
        cls.temp_dir.cleanup()

    def test_hospitals_cannot_access_each_others_patient_or_prescription(self):
        async def run_test():
            transport = self.httpx.ASGITransport(app=self.app)
            async with self.httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                alpha_headers = await create_facility_admin(
                    client,
                    username="alpha-admin",
                    email="alpha@example.com",
                    password="AlphaPass2026",
                    facility_name="Alpha Hospital",
                )
                beta_headers = await create_facility_admin(
                    client,
                    username="beta-admin",
                    email="beta@example.com",
                    password="BetaPass2026",
                    facility_name="Beta Hospital",
                )

                patient = await client.post(
                    "/api/v1/patients",
                    json={
                        "first_name": "Tenant",
                        "last_name": "Patient",
                        "date_of_birth": "1991-05-14",
                        "gender": "FEMALE",
                        "phone": "+234800000001",
                    },
                    headers={
                        **alpha_headers,
                        "Idempotency-Key": "test:tenant:alpha-patient",
                    },
                )
                self.assertEqual(patient.status_code, 201, patient.text)
                patient_id = patient.json()["id"]
                self.assertEqual(patient.json()["facility_slug"], "alpha-hospital")

                beta_patient_lookup = await client.get(
                    f"/api/v1/patients/{patient_id}",
                    headers=beta_headers,
                )
                self.assertEqual(beta_patient_lookup.status_code, 404, beta_patient_lookup.text)

                beta_patient_update = await client.put(
                    f"/api/v1/patients/{patient_id}",
                    json={"first_name": "Leaked"},
                    headers=beta_headers,
                )
                self.assertEqual(beta_patient_update.status_code, 404, beta_patient_update.text)

                beta_patient_timeline = await client.get(
                    f"/api/v1/patients/{patient_id}/timeline",
                    headers=beta_headers,
                )
                self.assertEqual(beta_patient_timeline.status_code, 404, beta_patient_timeline.text)

                alpha_lab_test = await client.post(
                    "/api/v1/laboratory/tests",
                    json={
                        "name": "Complete Blood Count",
                        "code": "CBC",
                        "category": "Haematology",
                        "price": 5000,
                    },
                    headers=alpha_headers,
                )
                self.assertEqual(alpha_lab_test.status_code, 201, alpha_lab_test.text)

                beta_lab_lookup = await client.get(
                    f"/api/v1/laboratory/tests/{alpha_lab_test.json()['id']}",
                    headers=beta_headers,
                )
                self.assertEqual(beta_lab_lookup.status_code, 404, beta_lab_lookup.text)

                beta_lab_list = await client.get(
                    "/api/v1/laboratory/tests",
                    headers=beta_headers,
                )
                self.assertEqual(beta_lab_list.status_code, 200, beta_lab_list.text)
                self.assertEqual(beta_lab_list.json(), [])

                beta_lab_test = await client.post(
                    "/api/v1/laboratory/tests",
                    json={
                        "name": "Complete Blood Count",
                        "code": "CBC",
                        "category": "Haematology",
                        "price": 4500,
                    },
                    headers=beta_headers,
                )
                self.assertEqual(beta_lab_test.status_code, 201, beta_lab_test.text)
                self.assertNotEqual(beta_lab_test.json()["id"], alpha_lab_test.json()["id"])

                medication = await client.post(
                    "/api/v1/pharmacy/medications",
                    json={
                        "name": "Tenant Capsule",
                        "code": "TEN-CAP-001",
                        "generic_name": "Tenantine",
                        "category": "Test",
                        "unit": "capsule",
                        "strength": "250mg",
                        "price": 250,
                        "reorder_level": 5,
                    },
                    headers=alpha_headers,
                )
                self.assertEqual(medication.status_code, 201, medication.text)

                beta_medication_lookup = await client.get(
                    f"/api/v1/pharmacy/medications/{medication.json()['id']}",
                    headers=beta_headers,
                )
                self.assertEqual(beta_medication_lookup.status_code, 404, beta_medication_lookup.text)

                beta_medication = await client.post(
                    "/api/v1/pharmacy/medications",
                    json={
                        "name": "Tenant Capsule",
                        "code": "TEN-CAP-001",
                        "generic_name": "Tenantine",
                        "category": "Test",
                        "unit": "capsule",
                        "strength": "250mg",
                        "price": 240,
                        "reorder_level": 5,
                    },
                    headers=beta_headers,
                )
                self.assertEqual(beta_medication.status_code, 201, beta_medication.text)
                self.assertNotEqual(beta_medication.json()["id"], medication.json()["id"])

                prescription = await client.post(
                    "/api/v1/pharmacy/prescriptions",
                    json={
                        "patient_id": patient_id,
                        "items": [
                            {
                                "medication_id": medication.json()["id"],
                                "quantity": 1,
                                "dosage": "One capsule daily",
                            }
                        ],
                    },
                    headers={
                        **alpha_headers,
                        "Idempotency-Key": "test:tenant:alpha-prescription",
                    },
                )
                self.assertEqual(prescription.status_code, 201, prescription.text)
                prescription_id = prescription.json()["id"]
                self.assertEqual(prescription.json()["status"], "PENDING")

                beta_cancel = await client.delete(
                    f"/api/v1/pharmacy/prescriptions/{prescription_id}",
                    headers=beta_headers,
                )
                self.assertEqual(beta_cancel.status_code, 404, beta_cancel.text)

                alpha_prescription_lookup = await client.get(
                    f"/api/v1/pharmacy/prescriptions/{prescription_id}",
                    headers=alpha_headers,
                )
                self.assertEqual(alpha_prescription_lookup.status_code, 200, alpha_prescription_lookup.text)
                self.assertEqual(alpha_prescription_lookup.json()["status"], "PENDING")

                upload = await client.post(
                    "/api/v1/files/upload",
                    data={"folder": "shared"},
                    files={"file": ("tenant.png", b"\x89PNG\r\n\x1a\nTENANT-A", "image/png")},
                    headers=alpha_headers,
                )
                self.assertEqual(upload.status_code, 201, upload.text)
                self.assertTrue(upload.json()["url"].startswith("/api/v1/files/content/"))
                self.assertIn("folder=shared", upload.json()["url"])

                async with self.httpx.AsyncClient(
                    transport=transport,
                    base_url="http://testserver",
                ) as anonymous_client:
                    anonymous_download = await anonymous_client.get(upload.json()["url"])
                    self.assertEqual(anonymous_download.status_code, 401, anonymous_download.text)

                alpha_download = await client.get(
                    upload.json()["url"],
                    headers=alpha_headers,
                )
                self.assertEqual(alpha_download.status_code, 200, alpha_download.text)
                self.assertIn(b"TENANT-A", alpha_download.content)

                beta_download = await client.get(
                    upload.json()["url"],
                    headers=beta_headers,
                )
                self.assertEqual(beta_download.status_code, 404, beta_download.text)

                beta_files = await client.get(
                    "/api/v1/files?folder=shared",
                    headers=beta_headers,
                )
                self.assertEqual(beta_files.status_code, 200, beta_files.text)
                self.assertEqual(beta_files.json()["total"], 0)

                beta_file_lookup = await client.get(
                    f"/api/v1/files/{upload.json()['filename']}?folder=shared",
                    headers=beta_headers,
                )
                self.assertEqual(beta_file_lookup.status_code, 404, beta_file_lookup.text)

        async def create_facility_admin(client, username, email, password, facility_name):
            auth = await client.post(
                "/api/v1/auth/ensure",
                json={
                    "username": username,
                    "email": email,
                    "password": password,
                    "role": "ADMIN",
                    "first_name": "Tenant",
                    "last_name": "Admin",
                },
            )
            self.assertEqual(auth.status_code, 200, auth.text)
            headers = {"Authorization": f"Bearer {auth.json()['access_token']}"}

            facility = await client.post(
                "/api/v1/facilities/ensure",
                json={
                    "name": facility_name,
                    "type": "hospital",
                    "country": "Nigeria",
                    "email": email,
                    "modules": ["reception", "records", "lab", "pharmacy"],
                },
                headers=headers,
            )
            self.assertEqual(facility.status_code, 200, facility.text)
            return headers

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
