import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


TENANT_A = "26cf1bb2-878f-4714-ab5a-c1379a2b91c9"
TENANT_B = "17260d68-d19d-431e-97bf-a4c8228d646b"


class OhmattOSIntegrationTest(unittest.TestCase):
    def setUp(self):
        from app.services.ohmattos_client import OhmattOSClient

        self.OhmattOSClient = OhmattOSClient
        self.temp_dir = tempfile.TemporaryDirectory()
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = private_key.public_key()
        self.key_path = Path(self.temp_dir.name) / "hispro-client.pem"
        self.key_path.write_bytes(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        self.base_env = {
            "APP_ENV": "development",
            "OHMATTOS_ENABLED": "true",
            "OHMATTOS_URL": "http://127.0.0.1:9000",
            "OHMATTOS_TOKEN_URL": "http://127.0.0.1:9000/api/v1/auth/token",
            "OHMATTOS_CLIENT_ID": "hispro-production",
            "OHMATTOS_CLIENT_PRIVATE_KEY_FILE": str(self.key_path),
            "OHMATTOS_CLIENT_KEY_ID": "hispro-2026-07",
            "OHMATTOS_CLIENT_SIGNING_ALG": "RS256",
            "OHMATTOS_TOKEN_AUDIENCE": "http://127.0.0.1:9000/api/v1/auth/token",
            "OHMATTOS_API_AUDIENCE": "ohmattos-api",
            "OHMATTOS_MAX_TOKEN_TTL_SECONDS": "300",
            "OHMATTOS_NOTIFICATIONS_ENABLED": "true",
            "OHMATTOS_JOBS_ENABLED": "true",
        }
        self.channel_setting = os.environ.get("HISPRO_PATIENT_NOTIFICATION_CHANNELS")

    def tearDown(self):
        if self.channel_setting is None:
            os.environ.pop("HISPRO_PATIENT_NOTIFICATION_CHANNELS", None)
        else:
            os.environ["HISPRO_PATIENT_NOTIFICATION_CHANNELS"] = self.channel_setting
        self.temp_dir.cleanup()

    def make_client(self, handler, **env_overrides):
        environ = {**self.base_env, **env_overrides}
        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        client = self.OhmattOSClient(environ=environ, http_client=http_client)
        self.addCleanup(http_client.close)
        return client

    @staticmethod
    def token_response(
        request,
        *,
        token="tenant-token",
        expires_in=300,
        tenant_id=None,
        scope=None,
        audience=None,
    ):
        form = parse_qs(request.content.decode("utf-8"))
        requested_tenant = form["tenant_id"][0]
        return httpx.Response(
            200,
            json={
                "access_token": token,
                "token_type": "Bearer",
                "expires_in": expires_in,
                "scope": scope or form["scope"][0],
                "tenant_id": tenant_id or requested_tenant,
                "audience": audience or form["audience"][0],
            },
        )

    def test_disabled_client_never_raises_or_posts(self):
        client = self.make_client(
            lambda _request: self.fail("disabled client attempted an HTTP request"),
            OHMATTOS_ENABLED="false",
        )
        result = client.submit_job(
            tenant_id=TENANT_A,
            job_type="hispro.test",
            payload={"safe": True},
        )
        self.assertFalse(result["ok"])
        self.assertIn("disabled", result["error"].lower())

    def test_feature_flags_require_complete_asymmetric_configuration(self):
        client = self.make_client(
            lambda request: self.token_response(request),
            OHMATTOS_JOBS_ENABLED="false",
        )
        self.assertFalse(client.feature_enabled("jobs"))

        client = self.make_client(
            lambda request: self.token_response(request),
            OHMATTOS_JOBS_ENABLED="true",
        )
        self.assertTrue(client.feature_enabled("jobs"))

        incomplete = self.OhmattOSClient(
            environ={
                "OHMATTOS_ENABLED": "true",
                "OHMATTOS_URL": "http://127.0.0.1:9000",
                "OHMATTOS_JOBS_ENABLED": "true",
            }
        )
        self.assertFalse(incomplete.feature_enabled("jobs"))

    def test_client_credentials_uses_private_key_jwt_and_tenant_allowlist_input(self):
        requests = []

        def handler(request):
            requests.append(request)
            if request.url.path == "/api/v1/auth/token":
                return self.token_response(request)
            return httpx.Response(202, json={"data": {"status": "queued"}})

        client = self.make_client(handler)
        result = client.send_notification(
            tenant_id=TENANT_A,
            user_id="patient:opaque-id",
            channel_type="email",
            recipient="patient@example.com",
            subject="Appointment reminder",
            body="Your appointment is tomorrow.",
            idempotency_key="hispro:patient-notification:email-1",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(len(requests), 2)
        token_request, service_request = requests
        form = parse_qs(token_request.content.decode("utf-8"))
        self.assertEqual(form["grant_type"], ["client_credentials"])
        self.assertEqual(form["client_id"], ["hispro-production"])
        self.assertEqual(
            form["client_assertion_type"],
            ["urn:ietf:params:oauth:client-assertion-type:jwt-bearer"],
        )
        self.assertEqual(form["tenant_id"], [TENANT_A])
        self.assertEqual(form["scope"], ["notifications:send"])
        self.assertEqual(form["audience"], ["ohmattos-api"])

        assertion = form["client_assertion"][0]
        header = jwt.get_unverified_header(assertion)
        claims = jwt.decode(
            assertion,
            self.public_key,
            algorithms=["RS256"],
            audience=self.base_env["OHMATTOS_TOKEN_AUDIENCE"],
            options={"verify_exp": False, "verify_iat": False, "verify_nbf": False},
        )
        self.assertEqual(header["kid"], "hispro-2026-07")
        self.assertEqual(claims["iss"], "hispro-production")
        self.assertEqual(claims["sub"], "hispro-production")
        self.assertEqual(claims["aud"], self.base_env["OHMATTOS_TOKEN_AUDIENCE"])
        self.assertLessEqual(claims["exp"] - claims["iat"], 60)
        self.assertTrue(claims["jti"])

        payload = json.loads(service_request.content)
        self.assertNotIn("app_id", payload)
        self.assertNotIn("tenant_id", payload)
        self.assertEqual(service_request.headers["authorization"], "Bearer tenant-token")
        self.assertEqual(
            service_request.headers["idempotency-key"],
            "hispro:patient-notification:email-1",
        )

    def test_token_cache_is_partitioned_by_tenant_and_scope(self):
        token_requests = []
        service_authorizations = []

        def handler(request):
            if request.url.path == "/api/v1/auth/token":
                form = parse_qs(request.content.decode("utf-8"))
                tenant_id = form["tenant_id"][0]
                token_requests.append((tenant_id, form["scope"][0]))
                return self.token_response(
                    request,
                    token=f"token-{tenant_id}",
                )
            service_authorizations.append(request.headers["authorization"])
            return httpx.Response(202, json={"data": {"status": "queued"}})

        client = self.make_client(handler)
        for tenant_id in (TENANT_A, TENANT_A, TENANT_B):
            result = client.send_notification(
                tenant_id=tenant_id,
                user_id="patient:opaque-id",
                channel_type="sms",
                recipient="+2348012345678",
                subject="",
                body="Your prescription is ready.",
                idempotency_key=f"notice:{tenant_id}",
            )
            self.assertTrue(result["ok"])

        self.assertEqual(
            token_requests,
            [
                (TENANT_A, "notifications:send"),
                (TENANT_B, "notifications:send"),
            ],
        )
        self.assertEqual(
            service_authorizations,
            [
                f"Bearer token-{TENANT_A}",
                f"Bearer token-{TENANT_A}",
                f"Bearer token-{TENANT_B}",
            ],
        )

    def test_unauthorized_service_response_refreshes_once(self):
        token_count = 0
        service_count = 0

        def handler(request):
            nonlocal token_count, service_count
            if request.url.path == "/api/v1/auth/token":
                token_count += 1
                return self.token_response(request, token=f"token-{token_count}")
            service_count += 1
            if service_count == 1:
                return httpx.Response(401, json={"error": "expired"})
            return httpx.Response(202, json={"data": {"status": "queued"}})

        client = self.make_client(handler)
        result = client.send_notification(
            tenant_id=TENANT_A,
            user_id="patient:opaque-id",
            channel_type="sms",
            recipient="+2348012345678",
            subject="",
            body="Reminder",
            idempotency_key="notice-refresh",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(token_count, 2)
        self.assertEqual(service_count, 2)

    def test_unsafe_token_response_is_rejected_before_service_call(self):
        service_calls = 0

        def wrong_tenant_handler(request):
            nonlocal service_calls
            if request.url.path == "/api/v1/auth/token":
                return self.token_response(request, tenant_id=TENANT_B)
            service_calls += 1
            return httpx.Response(202)

        client = self.make_client(wrong_tenant_handler)
        result = client.send_notification(
            tenant_id=TENANT_A,
            user_id="patient:opaque-id",
            channel_type="sms",
            recipient="+2348012345678",
            subject="",
            body="Reminder",
        )
        self.assertFalse(result["ok"])

        for response_overrides in (
            {"scope": "notifications:send logs:write"},
            {"audience": "wrong-api"},
            {"token": "x" * (16 * 1024 + 1)},
        ):
            client = self.make_client(
                lambda request, overrides=response_overrides: self.token_response(
                    request,
                    **overrides,
                )
            )
            result = client.send_notification(
                tenant_id=TENANT_A,
                user_id="patient:opaque-id",
                channel_type="sms",
                recipient="+2348012345678",
                subject="",
                body="Reminder",
            )
            self.assertFalse(result["ok"])
        self.assertEqual(service_calls, 0)

        client = self.make_client(
            lambda request: self.token_response(request, expires_in=301)
        )
        result = client.send_notification(
            tenant_id=TENANT_A,
            user_id="patient:opaque-id",
            channel_type="sms",
            recipient="+2348012345678",
            subject="",
            body="Reminder",
        )
        self.assertFalse(result["ok"])

    def test_production_rejects_legacy_master_api_key_and_plain_http(self):
        client = self.make_client(
            lambda request: self.token_response(request),
            APP_ENV="production",
            OHMATTOS_API_KEY="legacy-secret",
        )
        with self.assertRaisesRegex(Exception, "HTTPS|legacy"):
            client.validate_configuration(production=True)

        secure_env = {
            **self.base_env,
            "APP_ENV": "production",
            "OHMATTOS_URL": "https://ohmattos.example",
            "OHMATTOS_TOKEN_URL": "https://ohmattos.example/api/v1/auth/token",
            "OHMATTOS_TOKEN_AUDIENCE": "https://ohmattos.example/api/v1/auth/token",
            "OHMATTOS_API_KEY": "legacy-secret",
        }
        secure_client = self.OhmattOSClient(environ=secure_env)
        with self.assertRaisesRegex(Exception, "legacy OHMATTOS_API_KEY"):
            secure_client.validate_configuration(production=True)

    def test_notification_payload_matches_worker_contract_without_ownership_fields(self):
        captured = {}
        client = self.make_client(lambda request: self.token_response(request))

        def capture(path, payload, **options):
            captured["path"] = path
            captured["payload"] = payload
            captured["options"] = options
            return {"ok": True, "status": 202, "data": {"status": "queued"}}

        client._post = capture
        result = client.send_notification(
            tenant_id=TENANT_A,
            user_id="patient:opaque-id",
            channel_type="EMAIL",
            recipient="patient@example.com",
            subject="Appointment reminder",
            body="Your appointment is tomorrow.",
            idempotency_key="hispro:patient-notification:email-1",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(captured["path"], "/api/v1/notifications/send")
        self.assertEqual(captured["options"]["tenant_id"], TENANT_A)
        self.assertEqual(captured["options"]["scopes"], ("notifications:send",))
        self.assertNotIn("app_id", captured["payload"])
        self.assertNotIn("tenant_id", captured["payload"])
        self.assertEqual(
            captured["payload"]["content"],
            {
                "to": "patient@example.com",
                "subject": "Appointment reminder",
                "body": "Your appointment is tomorrow.",
            },
        )

    def test_idempotency_key_cannot_inject_an_http_header(self):
        calls = []
        client = self.make_client(lambda request: self.token_response(request))
        client._post = lambda *args, **kwargs: calls.append((args, kwargs))

        result = client.send_notification(
            tenant_id=TENANT_A,
            user_id="patient:opaque-id",
            channel_type="sms",
            recipient="+2348012345678",
            subject="",
            body="Reminder",
            idempotency_key="notice-1\r\nX-Injected: true",
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "Notification idempotency key is invalid")
        self.assertEqual(calls, [])

    def test_patient_notification_channels_are_explicit_and_deduplicated(self):
        from app.services.patient_notification_service import PatientNotificationService

        os.environ["HISPRO_PATIENT_NOTIFICATION_CHANNELS"] = (
            " portal, sms, email, SMS, invalid "
        )
        self.assertEqual(
            PatientNotificationService.configured_channels(),
            ["PORTAL", "SMS", "EMAIL"],
        )


if __name__ == "__main__":
    unittest.main()
