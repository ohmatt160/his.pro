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


class StaffChatTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.database_path = os.path.join(cls.temp_dir.name, "staff-chat.db")
        os.environ["DATABASE_URL"] = f"sqlite:///{cls.database_path}"
        os.environ["CHAT_UPLOAD_DIR"] = os.path.join(cls.temp_dir.name, "chat_uploads")
        os.environ["RATE_LIMIT_NAMESPACE"] = f"staff-chat-{os.path.basename(cls.temp_dir.name)}"

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

    def test_staff_chat_is_tenant_isolated_and_tracks_read_state(self):
        async def run_test():
            transport = self.httpx.ASGITransport(app=self.app)
            async with self.httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                alpha_admin = await self.create_facility_admin(
                    client,
                    username="alpha-chat-admin",
                    email="alpha-chat@example.com",
                    password="AlphaChat2026",
                    facility_name="Alpha Chat Hospital",
                )
                beta_admin = await self.create_facility_admin(
                    client,
                    username="beta-chat-admin",
                    email="beta-chat@example.com",
                    password="BetaChat2026",
                    facility_name="Beta Chat Hospital",
                )

                alpha_nurse = await self.create_staff(
                    client,
                    alpha_admin["headers"],
                    "alpha-chat-hospital",
                    "Nurse Alpha",
                    "nurse",
                    "alpha.nurse@example.com",
                )
                beta_nurse = await self.create_staff(
                    client,
                    beta_admin["headers"],
                    "beta-chat-hospital",
                    "Nurse Beta",
                    "nurse",
                    "beta.nurse@example.com",
                )

                alpha_staff_login = await client.post(
                    "/api/v1/auth/login?facility_slug=alpha-chat-hospital",
                    json={
                        "username": alpha_nurse["loginId"],
                        "password": alpha_nurse["temporaryPassword"],
                    },
                )
                self.assertEqual(alpha_staff_login.status_code, 200, alpha_staff_login.text)
                alpha_staff_headers = {"Authorization": f"Bearer {alpha_staff_login.json()['access_token']}"}

                staff_list = await client.get("/api/v1/chat/staff", headers=alpha_admin["headers"])
                self.assertEqual(staff_list.status_code, 200, staff_list.text)
                staff_ids = {member["id"] for member in staff_list.json()}
                self.assertIn(alpha_nurse["staffRecordId"], staff_ids)
                self.assertNotIn(beta_nurse["staffRecordId"], staff_ids)

                chat_health = await client.get("/api/v1/chat/health", headers=alpha_admin["headers"])
                self.assertEqual(chat_health.status_code, 200, chat_health.text)
                self.assertTrue(chat_health.json()["ok"])

                cross_tenant_conversation = await client.post(
                    "/api/v1/chat/conversations",
                    json={"participant_id": beta_nurse["staffRecordId"]},
                    headers=alpha_admin["headers"],
                )
                self.assertEqual(cross_tenant_conversation.status_code, 404, cross_tenant_conversation.text)

                first_conversation = await client.post(
                    "/api/v1/chat/conversations",
                    json={"participant_id": alpha_nurse["staffRecordId"]},
                    headers=alpha_admin["headers"],
                )
                self.assertEqual(first_conversation.status_code, 201, first_conversation.text)
                second_conversation = await client.post(
                    "/api/v1/chat/conversations",
                    json={"participant_id": alpha_nurse["staffRecordId"]},
                    headers=alpha_admin["headers"],
                )
                self.assertEqual(second_conversation.status_code, 201, second_conversation.text)
                self.assertEqual(first_conversation.json()["id"], second_conversation.json()["id"])

                conversation_id = first_conversation.json()["id"]
                sent_message = await client.post(
                    f"/api/v1/chat/conversations/{conversation_id}/messages",
                    json={"content": "Please review bay 2.", "message_type": "text"},
                    headers={
                        **alpha_admin["headers"],
                        "Idempotency-Key": "test:chat:message-send",
                    },
                )
                self.assertEqual(sent_message.status_code, 201, sent_message.text)
                self.assertFalse(sent_message.json()["is_read"])

                replayed_message = await client.post(
                    f"/api/v1/chat/conversations/{conversation_id}/messages",
                    json={"content": "Please review bay 2.", "message_type": "text"},
                    headers={
                        **alpha_admin["headers"],
                        "Idempotency-Key": "test:chat:message-send",
                    },
                )
                self.assertEqual(replayed_message.status_code, 200, replayed_message.text)
                self.assertEqual(replayed_message.json()["id"], sent_message.json()["id"])

                unread = await client.get("/api/v1/chat/unread-count", headers=alpha_staff_headers)
                self.assertEqual(unread.status_code, 200, unread.text)
                self.assertEqual(unread.json()["unread_count"], 1)

                messages = await client.get(
                    f"/api/v1/chat/conversations/{conversation_id}/messages",
                    headers=alpha_staff_headers,
                )
                self.assertEqual(messages.status_code, 200, messages.text)
                self.assertEqual(messages.json()[0]["content"], "Please review bay 2.")

                unread_after_read = await client.get("/api/v1/chat/unread-count", headers=alpha_staff_headers)
                self.assertEqual(unread_after_read.status_code, 200, unread_after_read.text)
                self.assertEqual(unread_after_read.json()["unread_count"], 0)

                spoofed_upload = await client.post(
                    "/api/v1/chat/upload",
                    files={"file": ("fake.png", b"not-a-png", "image/png")},
                    headers=alpha_staff_headers,
                )
                self.assertEqual(spoofed_upload.status_code, 400, spoofed_upload.text)

                valid_upload = await client.post(
                    "/api/v1/chat/upload",
                    files={"file": ("chat.png", b"\x89PNG\r\n\x1a\nsmall", "image/png")},
                    headers=alpha_staff_headers,
                )
                self.assertEqual(valid_upload.status_code, 201, valid_upload.text)
                self.assertTrue(valid_upload.json()["file_url"].startswith("/chat/files/"))

        asyncio.run(run_test())

    async def create_facility_admin(self, client, username, email, password, facility_name):
        auth = await client.post(
            "/api/v1/auth/ensure",
            json={
                "username": username,
                "email": email,
                "password": password,
                "role": "ADMIN",
                "first_name": "Facility",
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
                "modules": ["reception", "records", "nursing"],
            },
            headers=headers,
        )
        self.assertEqual(facility.status_code, 200, facility.text)
        return {"headers": headers, "facility": facility.json()}

    async def create_staff(self, client, headers, facility_slug, full_name, role, email):
        staff = await client.post(
            f"/api/v1/facilities/{facility_slug}/staff",
            json={
                "fullName": full_name,
                "role": role,
                "department": "General",
                "email": email,
                "password": "StaffChat2026",
            },
            headers=headers,
        )
        self.assertEqual(staff.status_code, 201, staff.text)
        return staff.json()


if __name__ == "__main__":
    unittest.main()
