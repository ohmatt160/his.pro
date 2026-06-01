import os
import sys
import tempfile
import unittest
import asyncio
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class SetupEndpointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.database_path = os.path.join(cls.temp_dir.name, "setup-test.db")
        os.environ["DATABASE_URL"] = f"sqlite:///{cls.database_path}"

        import httpx

        from app.main import app
        from app.extensions import Base, db_session, engine

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

    def test_setup_auth_and_facility_are_idempotent(self):
        async def run_test():
            transport = self.httpx.ASGITransport(app=self.app)
            async with self.httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client:
                await exercise_setup_flow(client)

        async def exercise_setup_flow(client):
            auth_payload = {
                "username": "sunrise-medical-centre-admin",
                "email": "admin@sunrise.example.com",
                "password": "Password1",
                "role": "ADMIN",
                "first_name": "Dr.",
                "last_name": "Amina Yusuf",
                "facility_slug": "sunrise-medical-centre",
            }

            first_auth = await client.post("/api/v1/auth/ensure", json=auth_payload)
            second_auth = await client.post("/api/v1/auth/ensure", json=auth_payload)

            self.assertEqual(first_auth.status_code, 200, first_auth.text)
            self.assertEqual(second_auth.status_code, 200, second_auth.text)
            self.assertIn("access_token", second_auth.json())

            facility_payload = {
                "name": "Sunrise Medical Centre",
                "type": "hospital",
                "country": "Nigeria",
                "phone": "+234 800 000 0000",
                "email": "admin@sunrise.example.com",
                "modules": ["reception", "records"],
                "settings": {
                    "administrator": {
                        "fullName": "Dr. Amina Yusuf",
                        "username": "sunrise-medical-centre-admin",
                    }
                },
            }
            headers = {"Authorization": f"Bearer {second_auth.json()['access_token']}"}

            first_facility = await client.post(
                "/api/v1/facilities/ensure", json=facility_payload, headers=headers
            )
            second_facility = await client.post(
                "/api/v1/facilities/ensure", json=facility_payload, headers=headers
            )

            self.assertEqual(first_facility.status_code, 200, first_facility.text)
            self.assertEqual(second_facility.status_code, 200, second_facility.text)
            self.assertEqual(first_facility.json()["id"], second_facility.json()["id"])
            self.assertEqual(second_facility.json()["slug"], "sunrise-medical-centre")

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
