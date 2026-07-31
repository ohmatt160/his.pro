import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tests.test_app_factory import import_isolated_app


class TenantRoutingEndpointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        database_path = os.path.join(cls.temp_dir.name, "tenant-routing.db")
        os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"
        os.environ["REDIS_URL"] = ""
        os.environ["RATE_LIMIT_NAMESPACE"] = "tenant-routing-test"

        app, Base, db_session, engine, httpx = import_isolated_app()
        Base.metadata.create_all(bind=engine)
        cls.app = app
        cls.db_session = db_session
        cls.engine = engine
        cls.httpx = httpx

        from app.models.facility import Facility

        cls.facility = Facility(
            name="Sunrise Medical Centre",
            type="hospital",
            slug="sunrise-medical-centre",
            modules=["reception", "records"],
            settings={},
            is_active=True,
        )
        cls.reserved_name_facility = Facility(
            name="API Clinic",
            type="clinic",
            slug="api",
            modules=["reception", "records"],
            settings={},
            is_active=True,
        )
        db_session.add_all([cls.facility, cls.reserved_name_facility])
        db_session.commit()
        cls.facility_identity = {
            "id": str(cls.facility.id),
            "slug": cls.facility.slug,
            "canonical_subdomain": cls.facility.canonical_subdomain,
        }
        cls.reserved_facility_identity = {
            "id": str(cls.reserved_name_facility.id),
            "slug": cls.reserved_name_facility.slug,
            "canonical_subdomain": cls.reserved_name_facility.canonical_subdomain,
        }

    @classmethod
    def tearDownClass(cls):
        cls.db_session.remove()
        cls.engine.dispose()
        cls.temp_dir.cleanup()

    def test_registered_hostname_resolves_to_same_immutable_tenant(self):
        async def exercise():
            transport = self.httpx.ASGITransport(app=self.app)
            async with self.httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                response = await client.get(
                    "/api/v1/facilities/resolve-host/sunrise-medical-centre"
                )
                self.assertEqual(response.status_code, 200, response.text)
                payload = response.json()
                self.assertEqual(
                    set(payload),
                    {"slug", "canonical_subdomain"},
                )
                self.assertEqual(payload["slug"], self.facility_identity["slug"])
                self.assertEqual(
                    payload["canonical_subdomain"],
                    self.facility_identity["canonical_subdomain"],
                )

        asyncio.run(exercise())

    def test_reserved_slug_uses_generated_subdomain_and_cannot_claim_reserved_host(self):
        canonical_subdomain = self.reserved_facility_identity["canonical_subdomain"]
        self.assertNotEqual(canonical_subdomain, "api")
        self.assertLessEqual(len(canonical_subdomain), 63)

        async def exercise():
            transport = self.httpx.ASGITransport(app=self.app)
            async with self.httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                reserved = await client.get("/api/v1/facilities/resolve-host/api")
                generated = await client.get(
                    "/api/v1/facilities/resolve-host/"
                    f"{canonical_subdomain}"
                )
                unknown = await client.get(
                    "/api/v1/facilities/resolve-host/unknown-hospital"
                )

                self.assertEqual(reserved.status_code, 404)
                self.assertEqual(unknown.status_code, 404)
                self.assertEqual(generated.status_code, 200, generated.text)
                self.assertEqual(
                    generated.json()["slug"],
                    self.reserved_facility_identity["slug"],
                )

        asyncio.run(exercise())

    def test_legacy_slug_resolver_returns_only_routing_metadata(self):
        async def exercise():
            transport = self.httpx.ASGITransport(app=self.app)
            async with self.httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                response = await client.get(
                    "/api/v1/facilities/resolve-workspace/sunrise-medical-centre"
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(
                    response.json(),
                    {
                        "slug": "sunrise-medical-centre",
                        "canonical_subdomain": "sunrise-medical-centre",
                    },
                )

        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
