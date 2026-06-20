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


class BranchIsolationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.database_path = os.path.join(cls.temp_dir.name, "branch-isolation.db")
        os.environ["DATABASE_URL"] = f"sqlite:///{cls.database_path}"
        os.environ["RATE_LIMIT_NAMESPACE"] = f"branch-isolation-{os.path.basename(cls.temp_dir.name)}"

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

    def test_branch_admins_cannot_see_each_others_patients(self):
        async def run_test():
            transport = self.httpx.ASGITransport(app=self.app)
            async with self.httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                owner_headers = await create_facility_admin(client)

                east = await client.post(
                    "/api/v1/facilities/campus-hospital/branches",
                    json={
                        "name": "East Clinic",
                        "location": "East Wing",
                        "modules": ["reception", "records", "pharmacy"],
                    },
                    headers=owner_headers,
                )
                self.assertEqual(east.status_code, 201, east.text)
                east_id = east.json()["id"]
                east_slug = east.json()["slug"]

                west = await client.post(
                    "/api/v1/facilities/campus-hospital/branches",
                    json={
                        "name": "West Clinic",
                        "location": "West Wing",
                        "modules": ["reception", "records", "pharmacy"],
                    },
                    headers=owner_headers,
                )
                self.assertEqual(west.status_code, 201, west.text)
                west_id = west.json()["id"]
                west_slug = west.json()["slug"]

                east_admin = await create_branch_admin(client, owner_headers, east_id, "east.admin@example.com", east_slug)
                west_admin = await create_branch_admin(client, owner_headers, west_id, "west.admin@example.com", west_slug)

                wrong_branch_login = await client.post(
                    f"/api/v1/auth/login?facility_slug=campus-hospital&branch_slug={east_slug}",
                    json={"username": "west-admin", "password": "BranchPass2026"},
                )
                self.assertEqual(wrong_branch_login.status_code, 401, wrong_branch_login.text)

                generic_branch_login = await client.post(
                    "/api/v1/auth/login?facility_slug=campus-hospital",
                    json={"username": "east-admin", "password": "BranchPass2026"},
                )
                self.assertEqual(generic_branch_login.status_code, 401, generic_branch_login.text)

                patient = await client.post(
                    "/api/v1/patients",
                    json={
                        "first_name": "Branch",
                        "last_name": "Patient",
                        "date_of_birth": "1992-04-08",
                        "gender": "FEMALE",
                        "phone": "+234800000100",
                    },
                    headers=east_admin,
                )
                self.assertEqual(patient.status_code, 201, patient.text)
                patient_body = patient.json()
                self.assertEqual(patient_body["branch_id"], east_id)

                east_list = await client.get("/api/v1/patients", headers=east_admin)
                self.assertEqual(east_list.status_code, 200, east_list.text)
                self.assertEqual(east_list.json()["total"], 1)

                west_list = await client.get("/api/v1/patients", headers=west_admin)
                self.assertEqual(west_list.status_code, 200, west_list.text)
                self.assertEqual(west_list.json()["total"], 0)

                west_lookup = await client.get(f"/api/v1/patients/{patient_body['id']}", headers=west_admin)
                self.assertEqual(west_lookup.status_code, 403, west_lookup.text)

        async def create_facility_admin(client):
            auth = await client.post(
                "/api/v1/auth/ensure",
                json={
                    "username": "campus-owner",
                    "email": "owner@example.com",
                    "password": "OwnerPass2026",
                    "role": "ADMIN",
                    "first_name": "Campus",
                    "last_name": "Owner",
                },
            )
            self.assertEqual(auth.status_code, 200, auth.text)
            headers = {"Authorization": f"Bearer {auth.json()['access_token']}"}

            facility = await client.post(
                "/api/v1/facilities/ensure",
                json={
                    "name": "Campus Hospital",
                    "type": "hospital",
                    "country": "Nigeria",
                    "email": "owner@example.com",
                    "modules": ["reception", "records", "pharmacy"],
                },
                headers=headers,
            )
            self.assertEqual(facility.status_code, 200, facility.text)
            return headers

        async def create_branch_admin(client, owner_headers, branch_id, email, branch_slug):
            staff = await client.post(
                "/api/v1/facilities/campus-hospital/staff",
                json={
                    "fullName": email.split("@")[0].replace(".", " ").title(),
                    "role": "branch_admin",
                    "department": "Administration",
                    "branchId": branch_id,
                    "email": email,
                    "password": "BranchPass2026",
                },
                headers=owner_headers,
            )
            self.assertEqual(staff.status_code, 201, staff.text)
            body = staff.json()
            login = await client.post(
                f"/api/v1/auth/login?facility_slug=campus-hospital&branch_slug={branch_slug}",
                json={"username": body["loginId"], "password": "BranchPass2026"},
            )
            self.assertEqual(login.status_code, 200, login.text)
            return {"Authorization": f"Bearer {login.json()['access_token']}"}

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()



