import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tests.test_app_factory import import_isolated_app


class DepartmentsPublicProfileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.database_path = os.path.join(cls.temp_dir.name, "departments-test.db")
        os.environ["DATABASE_URL"] = f"sqlite:///{cls.database_path}"
        os.environ["RATE_LIMIT_NAMESPACE"] = f"departments-test-{os.path.basename(cls.temp_dir.name)}"

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

    def test_departments_public_profile_and_referrals(self):
        async def run_test():
            transport = self.httpx.ASGITransport(app=self.app)
            async with self.httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client:
                auth = await client.post("/api/v1/auth/ensure", json={
                    "username": "buth-admin",
                    "email": "admin@buth.example.com",
                    "password": "ButhAdmin2026",
                    "role": "ADMIN",
                    "first_name": "Facility",
                    "last_name": "Admin",
                })
                self.assertEqual(auth.status_code, 200, auth.text)
                headers = {"Authorization": f"Bearer {auth.json()['access_token']}"}

                facility = await client.post("/api/v1/facilities/ensure", json={
                    "name": "BUTH Medical Campus",
                    "type": "hospital",
                    "country": "Nigeria",
                    "modules": ["reception", "records", "consultations", "pharmacy", "reports"],
                }, headers=headers)
                self.assertEqual(facility.status_code, 200, facility.text)
                self.assertEqual(facility.json()["hospital_type"], "single")
                self.assertEqual(facility.json()["departments"], [])

                settings = await client.put(
                    "/api/v1/facilities/buth-medical-campus/settings",
                    json={"hospital_type": "multi_clinic"},
                    headers=headers,
                )
                self.assertEqual(settings.status_code, 200, settings.text)
                self.assertEqual(settings.json()["hospital_type"], "multi_clinic")

                general = await client.post(
                    "/api/v1/facilities/buth-medical-campus/departments",
                    json={"name": "General Clinic", "location": "Main Building", "services": ["Reception", "Consultation"]},
                    headers=headers,
                )
                eye = await client.post(
                    "/api/v1/facilities/buth-medical-campus/departments",
                    json={"name": "Eye Clinic", "location": "East Wing", "services": ["Consultation"]},
                    headers=headers,
                )
                self.assertEqual(general.status_code, 201, general.text)
                self.assertEqual(eye.status_code, 201, eye.text)
                general_id = general.json()["id"]
                eye_id = eye.json()["id"]

                staff = await client.post(
                    "/api/v1/facilities/buth-medical-campus/staff",
                    json={
                        "fullName": "Dr Eye One",
                        "role": "doctor",
                        "department": "Eye Clinic",
                        "departmentId": eye_id,
                        "departmentIds": [eye_id],
                        "email": "eye.doctor@buth.example.com",
                        "password": "DoctorPass2026",
                    },
                    headers=headers,
                )
                self.assertEqual(staff.status_code, 201, staff.text)
                self.assertEqual(staff.json()["departmentId"], eye_id)

                blocked_delete = await client.delete(
                    f"/api/v1/facilities/buth-medical-campus/departments/{eye_id}",
                    headers=headers,
                )
                self.assertEqual(blocked_delete.status_code, 400, blocked_delete.text)

                profile = await client.put(
                    "/api/v1/facilities/buth-medical-campus/public-profile",
                    json={
                        "is_public": True,
                        "display_name": "BUTH Medical Campus",
                        "description": "Multi-clinic care campus.",
                        "phone": "+2348000000000",
                        "email": "frontdesk@buth.example.com",
                        "photos": [],
                        "departments": [
                            {
                                "id": general_id,
                                "is_visible": True,
                                "services": [{"name": "General Consultation", "price": 5000}],
                                "staff_ids": [],
                                "working_hours": {},
                                "photos": [],
                            }
                        ],
                    },
                    headers=headers,
                )
                self.assertEqual(profile.status_code, 200, profile.text)
                visible_general = next(d for d in profile.json()["departments"] if d["id"] == general_id)
                self.assertTrue(visible_general["is_visible"])
                self.assertEqual(visible_general["services"][0]["name"], "General Consultation")

                patient = await client.post(
                    "/api/v1/patients",
                    json={
                        "first_name": "Matt",
                        "last_name": "Whingan",
                        "date_of_birth": "1990-01-01",
                        "gender": "MALE",
                        "department_id": general_id,
                        "medical_history": {},
                    },
                    headers=headers,
                )
                self.assertEqual(patient.status_code, 201, patient.text)
                self.assertEqual(patient.json()["department_id"], general_id)

                referral = await client.post(
                    "/api/v1/referrals",
                    json={
                        "patient_id": patient.json()["id"],
                        "to_department_id": eye_id,
                        "reason": "Blurred vision",
                        "priority": "urgent",
                    },
                    headers=headers,
                )
                self.assertEqual(referral.status_code, 201, referral.text)
                self.assertEqual(referral.json()["to_department_id"], eye_id)

                accepted = await client.put(
                    f"/api/v1/referrals/{referral.json()['id']}/accept",
                    headers=headers,
                )
                self.assertEqual(accepted.status_code, 200, accepted.text)
                self.assertEqual(accepted.json()["status"], "accepted")

                eye_patients = await client.get(
                    f"/api/v1/patients?department_id={eye_id}",
                    headers=headers,
                )
                self.assertEqual(eye_patients.status_code, 200, eye_patients.text)
                self.assertEqual(eye_patients.json()["total"], 1)
                self.assertEqual(eye_patients.json()["patients"][0]["department_id"], eye_id)

        import asyncio
        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
