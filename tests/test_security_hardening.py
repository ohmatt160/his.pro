import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class SecurityHardeningTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.database_path = os.path.join(cls.temp_dir.name, "security-test.db")
        os.environ["DATABASE_URL"] = f"sqlite:///{cls.database_path}"
        os.environ["ALLOWED_ORIGINS"] = "https://his-pro.vercel.app"
        os.environ["RATE_LIMIT_NAMESPACE"] = f"security-test-{os.path.basename(cls.temp_dir.name)}"

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

    def test_security_controls(self):
        async def run_test():
            transport = self.httpx.ASGITransport(app=self.app)
            async with self.httpx.AsyncClient(
                transport=transport,
                base_url="https://testserver",
            ) as client:
                await self.exercise_security_controls(client)

        asyncio.run(run_test())

    async def exercise_security_controls(self, client):
        health = await client.get("/health")
        self.assertEqual(health.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(health.headers["X-Frame-Options"], "DENY")
        self.assertIn("default-src 'self'", health.headers["Content-Security-Policy"])

        cors = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "POST",
            },
        )
        self.assertNotIn("access-control-allow-origin", {k.lower(): v for k, v in cors.headers.items()})

        malicious = await client.get(
            "/api/v1/patients",
            params={"search": "' OR '1'='1"},
        )
        self.assertEqual(malicious.status_code, 400)

        weak_register = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "weak-admin",
                "email": "weak@example.com",
                "password": "Password1",
                "role": "ADMIN",
            },
        )
        self.assertEqual(weak_register.status_code, 400)
        self.assertIn("common", weak_register.text.lower())

        auth_payload = {
            "username": "secure-admin",
            "email": "secure@example.com",
            "password": "Secure2026",
            "role": "ADMIN",
        }
        auth = await client.post("/api/v1/auth/ensure", json=auth_payload)
        self.assertEqual(auth.status_code, 200, auth.text)
        self.assertIn("hispro_access_token", auth.headers.get("set-cookie", ""))
        self.assertIn("HttpOnly", auth.headers.get("set-cookie", ""))

        verify = await client.post("/api/v1/auth/verify")
        self.assertEqual(verify.status_code, 200, verify.text)
        self.assertEqual(verify.json()["username"], "secure-admin")

        bad_upload = await client.post(
            "/api/v1/files/upload",
            files={"file": ("receipt.png", b"not a real image", "image/png")},
            data={"folder": "../receipts"},
        )
        self.assertEqual(bad_upload.status_code, 400)

        logout_all = await client.post("/api/v1/auth/logout-everywhere")
        self.assertEqual(logout_all.status_code, 200, logout_all.text)

        rejected_after_logout = await client.post("/api/v1/auth/verify")
        self.assertEqual(rejected_after_logout.status_code, 401)

        for attempt in range(5):
            failed = await client.post(
                "/api/v1/auth/login",
                json={"username": "nobody", "password": "Secure2026"},
            )
            self.assertEqual(failed.status_code, 401, f"attempt {attempt}: {failed.text}")

        limited = await client.post(
            "/api/v1/auth/login",
            json={"username": "nobody", "password": "Secure2026"},
        )
        self.assertEqual(limited.status_code, 429)
        self.assertGreater(int(limited.headers["Retry-After"]), 0)
        self.assertEqual(limited.headers["X-RateLimit-Limit"], "5")


if __name__ == "__main__":
    unittest.main()
