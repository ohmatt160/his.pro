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


class SetupEndpointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.database_path = os.path.join(cls.temp_dir.name, "setup-test.db")
        os.environ["DATABASE_URL"] = f"sqlite:///{cls.database_path}"
        os.environ["RATE_LIMIT_NAMESPACE"] = f"setup-test-{os.path.basename(cls.temp_dir.name)}"

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
                "password": "Sunrise2026",
                "role": "ADMIN",
                "first_name": "Dr.",
                "last_name": "Amina Yusuf",
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
            self.assertEqual(second_facility.json()["tenant_id"], second_facility.json()["id"])
            self.assertEqual(second_facility.json()["slug"], "sunrise-medical-centre")
            self.assertEqual(
                second_facility.json()["canonical_subdomain"],
                "sunrise-medical-centre",
            )
            facility_id = second_facility.json()["id"]

            cold_workspace_lookup = await client.get(
                "/api/v1/facilities/sunrise-medical-centre",
                headers={"Authorization": f"Bearer {second_auth.json()['access_token']}"},
            )

            self.assertEqual(cold_workspace_lookup.status_code, 200, cold_workspace_lookup.text)
            self.assertEqual(cold_workspace_lookup.json()["slug"], "sunrise-medical-centre")
            self.assertEqual(cold_workspace_lookup.json()["tenant_id"], facility_id)
            self.assertEqual(cold_workspace_lookup.json()["modules"], ["reception", "records"])

            public_workspace_lookup = await client.get(
                "/api/v1/facilities/workspace/sunrise-medical-centre",
            )

            self.assertEqual(public_workspace_lookup.status_code, 200, public_workspace_lookup.text)
            self.assertEqual(public_workspace_lookup.json()["slug"], "sunrise-medical-centre")
            self.assertEqual(public_workspace_lookup.json()["modules"], ["reception", "records"])
            self.assertNotIn("tenant_id", public_workspace_lookup.json())
            self.assertNotIn("settings", public_workspace_lookup.json())
            self.assertNotIn("departments", public_workspace_lookup.json())
            self.assertNotIn("branches", public_workspace_lookup.json())
            self.assertNotIn("email", public_workspace_lookup.json())

            attacker_auth = await client.post(
                "/api/v1/auth/ensure",
                json={
                    "username": "unrelated-owner",
                    "email": "unrelated@example.com",
                    "password": "Unrelated2026",
                    "role": "ADMIN",
                },
            )
            self.assertEqual(attacker_auth.status_code, 200, attacker_auth.text)
            takeover = await client.post(
                "/api/v1/facilities/ensure",
                json=facility_payload,
                headers={
                    "Authorization": f"Bearer {attacker_auth.json()['access_token']}"
                },
            )
            self.assertEqual(takeover.status_code, 409, takeover.text)

            self_service_staff = await client.post(
                "/api/v1/auth/register",
                json={
                    "username": "self-service-doctor",
                    "email": "doctor@example.com",
                    "password": "DoctorSecure2026",
                    "role": "DOCTOR",
                    "facility_slug": "sunrise-medical-centre",
                },
            )
            self.assertEqual(self_service_staff.status_code, 400, self_service_staff.text)

            onboarded = await client.post(
                "/api/v1/auth/onboard",
                json={
                    "owner": {
                        "username": "greenfield-clinic-admin",
                        "email": "owner@greenfield.example.com",
                        "password": "Greenfield2026",
                        "first_name": "Greenfield",
                        "last_name": "Owner",
                    },
                    "facility": {
                        "name": "Greenfield Clinic",
                        "type": "clinic",
                        "country": "Nigeria",
                        "modules": ["reception", "billing"],
                    },
                },
            )
            self.assertEqual(onboarded.status_code, 200, onboarded.text)
            self.assertEqual(
                onboarded.json()["facility"]["slug"],
                "greenfield-clinic",
            )
            onboarding_retry = await client.post(
                "/api/v1/auth/onboard",
                json={
                    "owner": {
                        "username": "greenfield-clinic-admin",
                        "email": "owner@greenfield.example.com",
                        "password": "Greenfield2026",
                    },
                    "facility": {
                        "name": "Greenfield Clinic",
                        "type": "clinic",
                        "country": "Nigeria",
                        "modules": ["reception", "billing"],
                    },
                },
            )
            self.assertEqual(onboarding_retry.status_code, 200, onboarding_retry.text)
            self.assertEqual(
                onboarding_retry.json()["facility"]["id"],
                onboarded.json()["facility"]["id"],
            )

            canonical_host_lookup = await client.get(
                "/api/v1/facilities/resolve-host/sunrise-medical-centre",
            )
            self.assertEqual(canonical_host_lookup.status_code, 200, canonical_host_lookup.text)
            self.assertEqual(
                canonical_host_lookup.json(),
                {
                    "slug": "sunrise-medical-centre",
                    "canonical_subdomain": "sunrise-medical-centre",
                },
            )
            self.assertEqual(
                canonical_host_lookup.headers["cache-control"],
                "public, max-age=60, s-maxage=300, stale-while-revalidate=60",
            )

            for invalid_host in ["api", "unknown-hospital"]:
                missing_host_lookup = await client.get(
                    f"/api/v1/facilities/resolve-host/{invalid_host}",
                )
                self.assertEqual(missing_host_lookup.status_code, 404)

            email_login = await client.post(
                "/api/v1/auth/login?facility_slug=sunrise-medical-centre",
                json={
                    "username": "admin@sunrise.example.com",
                    "password": "Sunrise2026",
                },
            )

            self.assertEqual(email_login.status_code, 200, email_login.text)
            self.assertIn("access_token", email_login.json())

            profile = await client.get(
                "/api/v1/users/me",
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                },
            )

            self.assertEqual(profile.status_code, 200, profile.text)
            self.assertEqual(profile.json()["username"], "sunrise-medical-centre-admin")
            self.assertEqual(profile.json()["role"], "ADMIN")
            self.assertEqual(profile.json()["facility_id"], facility_id)
            self.assertEqual(profile.json()["facility_slug"], "sunrise-medical-centre")

            active_sessions = await client.get(
                "/api/v1/auth/sessions",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(active_sessions.status_code, 200, active_sessions.text)
            self.assertGreaterEqual(len(active_sessions.json()), 1)
            self.assertTrue(any(session["is_current"] for session in active_sessions.json()))

            empty_dashboard = await client.get(
                "/api/v1/dashboard/stats?facility_slug=sunrise-medical-centre",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(empty_dashboard.status_code, 200, empty_dashboard.text)
            self.assertEqual(empty_dashboard.json()["patient_count"], 0)
            self.assertEqual(empty_dashboard.json()["active_queue_count"], 0)

            facility_update = await client.put(
                "/api/v1/facilities/sunrise-medical-centre",
                json={
                    "phone": "+234 800 999 0000",
                    "address": "Updated Hospital Road",
                    "settings": {"timezone": "Africa/Lagos"},
                },
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(facility_update.status_code, 200, facility_update.text)
            self.assertEqual(facility_update.json()["slug"], "sunrise-medical-centre")
            self.assertEqual(facility_update.json()["phone"], "+234 800 999 0000")
            self.assertEqual(facility_update.json()["settings"]["timezone"], "Africa/Lagos")

            profile_update = await client.put(
                "/api/v1/users/me",
                json={
                    "first_name": "Dr",
                    "last_name": "Amina Yusuf",
                    "phone": "+234 800 999 1111",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "X-Forwarded-For": "203.0.113.42",
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Safari/604.1",
                },
            )

            self.assertEqual(profile_update.status_code, 200, profile_update.text)
            self.assertEqual(profile_update.json()["phone"], "+234 800 999 1111")

            audit_logs = await client.get(
                "/api/v1/audit-logs?limit=20",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(audit_logs.status_code, 200, audit_logs.text)
            profile_event = next(
                log for log in audit_logs.json() if log["action"] == "UPDATE_PROFILE"
            )
            # Untrusted forwarding headers must not override the direct peer IP.
            self.assertEqual(profile_event["ip_address"], "127.0.0.1")
            self.assertIn("iPhone", profile_event["user_agent"])

            disabled_lab_access = await client.get(
                "/api/v1/laboratory/tests",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(disabled_lab_access.status_code, 403, disabled_lab_access.text)

            invalid_modules_update = await client.put(
                "/api/v1/facilities/sunrise-medical-centre/modules",
                json=["reception", "unknown-module"],
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(invalid_modules_update.status_code, 400, invalid_modules_update.text)

            modules_update = await client.put(
                "/api/v1/facilities/sunrise-medical-centre/modules",
                json=[
                    "patients",
                    "records",
                    "consultations",
                    "nursing",
                    "lab",
                    "pharmacy",
                    "billing",
                    "radiology",
                    "inventory",
                    "reports",
                ],
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(modules_update.status_code, 200, modules_update.text)
            self.assertEqual(
                modules_update.json()["modules"],
                [
                    "reception",
                    "records",
                    "consultations",
                    "nursing",
                    "lab",
                    "pharmacy",
                    "billing",
                    "radiology",
                    "inventory",
                    "reports",
                ],
            )

            for report_path in [
                "/api/v1/reports/summary?date_from=2026-01-01&date_to=2026-12-31",
                "/api/v1/reports/revenue?date_from=2026-01-01&date_to=2026-12-31",
                "/api/v1/reports/departments?date_from=2026-01-01&date_to=2026-12-31",
                "/api/v1/reports/operations?date_from=2026-01-01&date_to=2026-12-31",
                "/api/v1/reports/inventory",
            ]:
                empty_report = await client.get(
                    report_path,
                    headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
                )
                self.assertEqual(empty_report.status_code, 200, empty_report.text)

            missing_patient_id = "missing-patient-id"
            for list_path in [
                f"/api/v1/appointments?patient_id={missing_patient_id}",
                f"/api/v1/billing/invoices?patient_id={missing_patient_id}",
                f"/api/v1/emr?patient_id={missing_patient_id}",
                f"/api/v1/laboratory/orders?patient_id={missing_patient_id}",
                f"/api/v1/pharmacy/prescriptions?patient_id={missing_patient_id}",
                f"/api/v1/radiology?patient_id={missing_patient_id}",
                f"/api/v1/patient-notifications?patient_id={missing_patient_id}",
                f"/api/v1/order-workflow?patient_id={missing_patient_id}",
            ]:
                empty_list = await client.get(
                    list_path,
                    headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
                )
                self.assertEqual(empty_list.status_code, 200, empty_list.text)
                self.assertEqual(empty_list.json(), [])

            staff_payload = {
                "fullName": "Nurse Ada Okafor",
                "role": "nurse",
                "department": "Nursing",
                "email": "ada.okafor@sunrise.example.com",
                "phone": "+234 800 111 2222",
                "createdBy": "Dr. Amina Yusuf",
            }
            staff_create = await client.post(
                "/api/v1/facilities/sunrise-medical-centre/staff",
                json=staff_payload,
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(staff_create.status_code, 201, staff_create.text)
            self.assertEqual(staff_create.json()["facilityId"], facility_id)
            self.assertEqual(staff_create.json()["loginId"], "sunrise-medical-centre-NUR-001")
            self.assertEqual(staff_create.json()["role"], "nurse")
            self.assertTrue(staff_create.json()["temporaryPassword"])

            staff_update = await client.put(
                f"/api/v1/facilities/sunrise-medical-centre/staff/{staff_create.json()['staffRecordId']}",
                json={
                    "fullName": "Nurse Ada Okafor",
                    "role": "nurse",
                    "department": "Nursing",
                    "phone": "+234 800 111 3333",
                    "password": "NurseAda2026",
                },
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(staff_update.status_code, 200, staff_update.text)
            self.assertEqual(staff_update.json()["phone"], "+234 800 111 3333")
            self.assertEqual(staff_update.json()["temporaryPassword"], "NurseAda2026")

            admin_update_by_legacy_login = await client.put(
                "/api/v1/facilities/sunrise-medical-centre/staff/SUNRISE-MEDICAL-CENTRE-ADMIN",
                json={"fullName": "Dr. Amina Yusuf"},
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )
            self.assertEqual(
                admin_update_by_legacy_login.status_code,
                200,
                admin_update_by_legacy_login.text,
            )
            self.assertEqual(
                admin_update_by_legacy_login.json()["loginId"],
                "sunrise-medical-centre-admin",
            )

            doctor_create = await client.post(
                "/api/v1/facilities/sunrise-medical-centre/staff",
                json={
                    "fullName": "Dr. Chidi Nwosu",
                    "role": "doctor",
                    "department": "Consultations",
                    "email": "chidi.nwosu@sunrise.example.com",
                    "phone": "+234 800 222 3333",
                    "createdBy": "Dr. Amina Yusuf",
                },
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(doctor_create.status_code, 201, doctor_create.text)
            self.assertEqual(doctor_create.json()["loginId"], "sunrise-medical-centre-DOC-001")
            self.assertEqual(doctor_create.json()["role"], "doctor")

            billing_staff_create = await client.post(
                "/api/v1/facilities/sunrise-medical-centre/staff",
                json={
                    "fullName": "Ada Revenue",
                    "role": "billing",
                    "department": "Revenue & Billing",
                    "email": "ada.revenue@sunrise.example.com",
                    "phone": "+234 800 333 4444",
                    "password": "BillingAda2026",
                    "createdBy": "Dr. Amina Yusuf",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                },
            )
            self.assertEqual(
                billing_staff_create.status_code,
                201,
                billing_staff_create.text,
            )
            self.assertEqual(
                billing_staff_create.json()["loginId"],
                "sunrise-medical-centre-BIL-001",
            )
            self.assertEqual(billing_staff_create.json()["role"], "billing")

            billing_login = await client.post(
                "/api/v1/auth/login?facility_slug=sunrise-medical-centre",
                json={
                    "username": billing_staff_create.json()["loginId"],
                    "password": "BillingAda2026",
                },
            )
            self.assertEqual(billing_login.status_code, 200, billing_login.text)
            billing_headers = {
                "Authorization": f"Bearer {billing_login.json()['access_token']}"
            }
            billing_options = await client.get(
                "/api/v1/patients/options",
                headers=billing_headers,
            )
            self.assertEqual(billing_options.status_code, 200, billing_options.text)
            billing_patient_registry = await client.get(
                "/api/v1/patients",
                headers=billing_headers,
            )
            self.assertEqual(billing_patient_registry.status_code, 403)
            billing_medical_records = await client.get(
                "/api/v1/emr",
                headers=billing_headers,
            )
            self.assertEqual(billing_medical_records.status_code, 403)
            billing_tasks = await client.get(
                "/api/v1/tasks",
                headers=billing_headers,
            )
            self.assertEqual(billing_tasks.status_code, 200, billing_tasks.text)

            staff_list = await client.get(
                "/api/v1/facilities/sunrise-medical-centre/staff",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(staff_list.status_code, 200, staff_list.text)
            self.assertEqual(
                [member["loginId"] for member in staff_list.json()],
                [
                    "sunrise-medical-centre-admin",
                    "sunrise-medical-centre-NUR-001",
                    "sunrise-medical-centre-DOC-001",
                    "sunrise-medical-centre-BIL-001",
                ],
            )
            self.assertEqual(
                {member["facilityId"] for member in staff_list.json()},
                {facility_id},
            )

            clinicians = await client.get(
                "/api/v1/facilities/sunrise-medical-centre/clinicians",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(clinicians.status_code, 200, clinicians.text)
            self.assertEqual(
                {member["loginId"] for member in clinicians.json()},
                {"sunrise-medical-centre-admin", "sunrise-medical-centre-DOC-001"},
            )

            staff_lookup = await client.get(
                "/api/v1/facilities/sunrise-medical-centre/staff/sunrise-medical-centre-NUR-001",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(staff_lookup.status_code, 200, staff_lookup.text)
            self.assertEqual(staff_lookup.json()["fullName"], "Nurse Ada Okafor")

            staff_login = await client.post(
                "/api/v1/auth/login?facility_slug=sunrise-medical-centre",
                json={
                    "username": "sunrise-medical-centre-NUR-001",
                    "password": "NurseAda2026",
                },
            )

            self.assertEqual(staff_login.status_code, 200, staff_login.text)

            staff_profile = await client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {staff_login.json()['access_token']}"},
            )

            self.assertEqual(staff_profile.status_code, 200, staff_profile.text)
            self.assertEqual(staff_profile.json()["role"], "NURSE")
            self.assertEqual(staff_profile.json()["facility_id"], facility_id)
            self.assertEqual(staff_profile.json()["facility_slug"], "sunrise-medical-centre")

            nurse_lab_access_denied = await client.get(
                "/api/v1/laboratory/tests",
                headers={"Authorization": f"Bearer {staff_login.json()['access_token']}"},
            )

            self.assertEqual(nurse_lab_access_denied.status_code, 403, nurse_lab_access_denied.text)

            nurse_cross_role_tasks_denied = await client.get(
                "/api/v1/tasks?role=LAB_TECH",
                headers={"Authorization": f"Bearer {staff_login.json()['access_token']}"},
            )

            self.assertEqual(nurse_cross_role_tasks_denied.status_code, 403, nurse_cross_role_tasks_denied.text)

            facility_alert = await client.post(
                "/api/v1/alerts",
                json={
                    "alert_type": "warning",
                    "title": "Stock review",
                    "message": "Review low-stock supplies before evening handover.",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:facility-alert",
                },
            )

            self.assertEqual(facility_alert.status_code, 201, facility_alert.text)
            self.assertIsNone(facility_alert.json()["recipient_id"])

            facility_alert_replay = await client.post(
                "/api/v1/alerts",
                json={
                    "alert_type": "warning",
                    "title": "Stock review",
                    "message": "Review low-stock supplies before evening handover.",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:facility-alert",
                },
            )
            self.assertEqual(facility_alert_replay.status_code, 200, facility_alert_replay.text)
            self.assertEqual(facility_alert_replay.json()["id"], facility_alert.json()["id"])

            staff_alert = await client.post(
                "/api/v1/alerts",
                json={
                    "alert_type": "critical",
                    "title": "Ward escalation",
                    "message": "Please review the observation ward immediately.",
                    "recipient_id": staff_profile.json()["id"],
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:staff-alert",
                },
            )

            self.assertEqual(staff_alert.status_code, 201, staff_alert.text)
            self.assertEqual(staff_alert.json()["recipient_id"], staff_profile.json()["id"])

            admin_alert_list = await client.get(
                "/api/v1/alerts?per_page=100",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(admin_alert_list.status_code, 200, admin_alert_list.text)
            self.assertEqual(
                [alert["title"] for alert in admin_alert_list.json()],
                ["Stock review"],
            )

            admin_staff_alert_lookup = await client.get(
                f"/api/v1/alerts/{staff_alert.json()['id']}",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(admin_staff_alert_lookup.status_code, 404, admin_staff_alert_lookup.text)

            staff_alert_list = await client.get(
                "/api/v1/alerts?per_page=100",
                headers={"Authorization": f"Bearer {staff_login.json()['access_token']}"},
            )

            self.assertEqual(staff_alert_list.status_code, 200, staff_alert_list.text)
            self.assertEqual(
                sorted(alert["title"] for alert in staff_alert_list.json()),
                ["Stock review", "Ward escalation"],
            )

            staff_alert_read = await client.put(
                f"/api/v1/alerts/{staff_alert.json()['id']}/read",
                headers={"Authorization": f"Bearer {staff_login.json()['access_token']}"},
            )

            self.assertEqual(staff_alert_read.status_code, 200, staff_alert_read.text)
            self.assertTrue(staff_alert_read.json()["is_read"])

            nurse_role_alert = await client.post(
                "/api/v1/alerts/role",
                json={
                    "alert_type": "info",
                    "title": "Nursing huddle",
                    "message": "Nursing team huddle starts at 4 PM.",
                    "recipient_role": "NURSE",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:nurse-role-alert",
                },
            )

            self.assertEqual(nurse_role_alert.status_code, 201, nurse_role_alert.text)
            self.assertEqual(len(nurse_role_alert.json()), 1)

            staff_role_alert_list = await client.get(
                "/api/v1/alerts?per_page=100",
                headers={"Authorization": f"Bearer {staff_login.json()['access_token']}"},
            )

            self.assertEqual(staff_role_alert_list.status_code, 200, staff_role_alert_list.text)
            self.assertIn(
                "Nursing huddle",
                {alert["title"] for alert in staff_role_alert_list.json()},
            )

            audit_log_list = await client.get(
                "/api/v1/audit-logs?action=CREATE_ALERT&limit=20",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(audit_log_list.status_code, 200, audit_log_list.text)
            self.assertEqual(len(audit_log_list.json()), 2)
            self.assertEqual(
                {entry["facility_slug"] for entry in audit_log_list.json()},
                {"sunrise-medical-centre"},
            )
            self.assertEqual(
                {entry["details"]["title"] for entry in audit_log_list.json()},
                {"Stock review", "Ward escalation"},
            )

            settings_audit_log_list = await client.get(
                "/api/v1/audit-logs?limit=200",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(settings_audit_log_list.status_code, 200, settings_audit_log_list.text)
            self.assertIn(
                "UPDATE_FACILITY",
                {entry["action"] for entry in settings_audit_log_list.json()},
            )
            self.assertIn(
                "UPDATE_PROFILE",
                {entry["action"] for entry in settings_audit_log_list.json()},
            )
            self.assertIn(
                "UPDATE_FACILITY_MODULES",
                {entry["action"] for entry in settings_audit_log_list.json()},
            )

            staff_audit_denied = await client.get(
                "/api/v1/audit-logs?limit=20",
                headers={"Authorization": f"Bearer {staff_login.json()['access_token']}"},
            )

            self.assertEqual(staff_audit_denied.status_code, 403, staff_audit_denied.text)

            patient_payload = {
                "first_name": "Musa",
                "last_name": "Bello",
                "date_of_birth": "1990-04-12",
                "gender": "MALE",
                "phone": "+234 800 333 4444",
                "email": "musa.bello@example.com",
                "address": "12 Hospital Road",
                "blood_type": "O+",
                "medical_history": {},
                "emergency_contact_name": "Aisha Bello",
                "emergency_contact_phone": "+234 800 555 6666",
            }
            patient_create = await client.post(
                "/api/v1/patients",
                json=patient_payload,
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:musa-bello",
                },
            )

            self.assertEqual(patient_create.status_code, 201, patient_create.text)
            self.assertEqual(patient_create.json()["full_name"], "Musa Bello")
            self.assertEqual(patient_create.json()["facility_slug"], "sunrise-medical-centre")

            patient_replay = await client.post(
                "/api/v1/patients",
                json=patient_payload,
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:musa-bello",
                },
            )
            self.assertEqual(patient_replay.status_code, 200, patient_replay.text)
            self.assertEqual(patient_replay.json()["id"], patient_create.json()["id"])

            patient_key_conflict = await client.post(
                "/api/v1/patients",
                json={**patient_payload, "first_name": "Another"},
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:musa-bello",
                },
            )
            self.assertEqual(patient_key_conflict.status_code, 409)

            patient_list = await client.get(
                "/api/v1/patients?search=Musa",
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                },
            )

            self.assertEqual(patient_list.status_code, 200, patient_list.text)
            self.assertEqual(patient_list.json()["total"], 1)
            self.assertEqual(patient_list.json()["patients"][0]["full_name"], "Musa Bello")

            private_patient_create = await client.post(
                "/api/v1/patients",
                json={
                    "first_name": "Private",
                    "last_name": "Case",
                    "date_of_birth": "1985-01-15",
                    "gender": "FEMALE",
                    "phone": "+234 800 777 8888",
                    "medical_history": {},
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:private-case",
                },
            )

            self.assertEqual(private_patient_create.status_code, 201, private_patient_create.text)

            medical_record_create = await client.post(
                "/api/v1/emr",
                json={
                    "patient_id": patient_create.json()["id"],
                    "chief_complaint": "Fever and cough",
                    "vital_signs": {
                        "temperature": "38.2",
                        "blood_pressure": "120/80",
                        "pulse": "88",
                    },
                    "symptoms": ["fever", "cough"],
                    "diagnosis": ["Upper respiratory tract infection"],
                    "treatment_plan": "Hydration and symptomatic management",
                    "follow_up_date": "2026-06-08",
                    "notes": "Return if symptoms worsen",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:medical-record",
                },
            )

            self.assertEqual(medical_record_create.status_code, 201, medical_record_create.text)
            self.assertEqual(medical_record_create.json()["facility_slug"], "sunrise-medical-centre")
            self.assertEqual(medical_record_create.json()["chief_complaint"], "Fever and cough")
            self.assertEqual(
                medical_record_create.json()["diagnosis"],
                ["Upper respiratory tract infection"],
            )
            medical_record_replay = await client.post(
                "/api/v1/emr",
                json={
                    "patient_id": patient_create.json()["id"],
                    "chief_complaint": "Fever and cough",
                    "vital_signs": {
                        "temperature": "38.2",
                        "blood_pressure": "120/80",
                        "pulse": "88",
                    },
                    "symptoms": ["fever", "cough"],
                    "diagnosis": ["Upper respiratory tract infection"],
                    "treatment_plan": "Hydration and symptomatic management",
                    "follow_up_date": "2026-06-08",
                    "notes": "Return if symptoms worsen",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:medical-record",
                },
            )
            self.assertEqual(medical_record_replay.status_code, 200, medical_record_replay.text)
            self.assertEqual(medical_record_replay.json()["id"], medical_record_create.json()["id"])

            medical_record_list = await client.get(
                f"/api/v1/emr?patient_id={patient_create.json()['id']}",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(medical_record_list.status_code, 200, medical_record_list.text)
            self.assertEqual(len(medical_record_list.json()), 1)

            medical_record_update = await client.put(
                f"/api/v1/emr/{medical_record_create.json()['id']}",
                json={"notes": "Improving after treatment"},
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(medical_record_update.status_code, 200, medical_record_update.text)
            self.assertEqual(medical_record_update.json()["notes"], "Improving after treatment")

            medical_record_void = await client.delete(
                f"/api/v1/emr/{medical_record_create.json()['id']}?reason=Entered%20for%20the%20wrong%20encounter",
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                },
            )
            self.assertEqual(
                medical_record_void.status_code,
                200,
                medical_record_void.text,
            )
            medical_record_after_void = await client.get(
                f"/api/v1/emr/{medical_record_create.json()['id']}",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )
            self.assertEqual(
                medical_record_after_void.status_code,
                200,
                medical_record_after_void.text,
            )
            self.assertEqual(medical_record_after_void.json()["status"], "VOIDED")
            self.assertEqual(
                medical_record_after_void.json()["void_reason"],
                "Entered for the wrong encounter",
            )
            blocked_voided_record_update = await client.put(
                f"/api/v1/emr/{medical_record_create.json()['id']}",
                json={"notes": "This must not replace retained history"},
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )
            self.assertEqual(blocked_voided_record_update.status_code, 409)

            appointment_create = await client.post(
                "/api/v1/appointments",
                json={
                    "patient_id": patient_create.json()["id"],
                    "doctor_id": doctor_create.json()["staffRecordId"],
                    "appointment_date": "2026-06-01T10:30:00",
                    "duration_minutes": 30,
                    "reason": "Initial consultation",
                    "notes": "First scheduled visit",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:appointment",
                },
            )

            self.assertEqual(appointment_create.status_code, 201, appointment_create.text)
            self.assertEqual(appointment_create.json()["facility_slug"], "sunrise-medical-centre")
            self.assertEqual(appointment_create.json()["doctor_id"], doctor_create.json()["staffRecordId"])
            self.assertEqual(appointment_create.json()["duration_minutes"], 30)
            appointment_replay = await client.post(
                "/api/v1/appointments",
                json={
                    "patient_id": patient_create.json()["id"],
                    "doctor_id": doctor_create.json()["staffRecordId"],
                    "appointment_date": "2026-06-01T10:30:00",
                    "duration_minutes": 30,
                    "reason": "Initial consultation",
                    "notes": "First scheduled visit",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:appointment",
                },
            )
            self.assertEqual(appointment_replay.status_code, 200, appointment_replay.text)
            self.assertEqual(appointment_replay.json()["id"], appointment_create.json()["id"])

            doctor_login = await client.post(
                "/api/v1/auth/login?facility_slug=sunrise-medical-centre",
                json={
                    "username": "sunrise-medical-centre-DOC-001",
                    "password": doctor_create.json()["temporaryPassword"],
                },
            )

            self.assertEqual(doctor_login.status_code, 200, doctor_login.text)
            doctor_headers = {"Authorization": f"Bearer {doctor_login.json()['access_token']}"}

            doctor_patient_list = await client.get(
                "/api/v1/patients?search=Musa",
                headers=doctor_headers,
            )
            self.assertEqual(doctor_patient_list.status_code, 200, doctor_patient_list.text)
            self.assertEqual(doctor_patient_list.json()["total"], 1)
            self.assertEqual(doctor_patient_list.json()["patients"][0]["id"], patient_create.json()["id"])

            doctor_private_patient_list = await client.get(
                "/api/v1/patients?search=Private",
                headers=doctor_headers,
            )
            self.assertEqual(doctor_private_patient_list.status_code, 200, doctor_private_patient_list.text)
            self.assertEqual(doctor_private_patient_list.json()["total"], 0)

            doctor_private_patient_lookup = await client.get(
                f"/api/v1/patients/{private_patient_create.json()['id']}",
                headers=doctor_headers,
            )
            self.assertEqual(doctor_private_patient_lookup.status_code, 403, doctor_private_patient_lookup.text)

            appointment_notifications = await client.get(
                f"/api/v1/patient-notifications?patient_id={patient_create.json()['id']}&notification_type=appointment_reminder",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(appointment_notifications.status_code, 200, appointment_notifications.text)
            self.assertEqual(
                {notice["channel"] for notice in appointment_notifications.json()},
                {"PORTAL", "SMS"},
            )

            appointment_list = await client.get(
                "/api/v1/appointments",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(appointment_list.status_code, 200, appointment_list.text)
            self.assertEqual(len(appointment_list.json()), 1)

            doctor_appointment_list = await client.get(
                f"/api/v1/appointments?doctor_id={doctor_create.json()['staffRecordId']}",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(doctor_appointment_list.status_code, 200, doctor_appointment_list.text)
            self.assertEqual(len(doctor_appointment_list.json()), 1)

            consultation_start = await client.post(
                "/api/v1/consultations/start",
                json={
                    "patient_id": patient_create.json()["id"],
                    "appointment_id": appointment_create.json()["id"],
                    "chief_complaint": "Fever, cough, and malaise",
                },
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(consultation_start.status_code, 201, consultation_start.text)
            self.assertEqual(consultation_start.json()["patient_name"], "Musa Bello")
            self.assertEqual(consultation_start.json()["appointment_status"], "IN_PROGRESS")

            consultation_update = await client.put(
                f"/api/v1/consultations/{consultation_start.json()['id']}",
                json={
                    "vital_signs": {"temperature": "38.1", "pulse": "92"},
                    "symptoms": ["Fever", "Cough"],
                    "diagnosis": ["Upper respiratory tract infection"],
                    "treatment_plan": "Oral medication, fluids, and review in 3 days.",
                    "prescriptions": [
                        {"medication": "Paracetamol", "dose": "500mg", "frequency": "TDS"}
                    ],
                    "lab_orders": [{"test": "Full Blood Count"}],
                    "radiology_orders": [{"study": "Chest X-ray"}],
                    "follow_up_date": "2026-06-04",
                    "notes": "Patient stable for outpatient management.",
                },
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(consultation_update.status_code, 200, consultation_update.text)
            self.assertEqual(consultation_update.json()["status"], "in_progress")
            self.assertEqual(consultation_update.json()["radiology_orders"][0]["type"], "radiology")

            consultation_lab_orders = await client.get(
                f"/api/v1/laboratory/orders?patient_id={patient_create.json()['id']}",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(consultation_lab_orders.status_code, 200, consultation_lab_orders.text)
            self.assertEqual(len(consultation_lab_orders.json()), 1)

            consultation_radiology_orders = await client.get(
                f"/api/v1/radiology?patient_id={patient_create.json()['id']}&per_page=100",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(consultation_radiology_orders.status_code, 200, consultation_radiology_orders.text)
            self.assertEqual(len(consultation_radiology_orders.json()), 1)

            consultation_prescriptions = await client.get(
                f"/api/v1/pharmacy/prescriptions?patient_id={patient_create.json()['id']}",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(consultation_prescriptions.status_code, 200, consultation_prescriptions.text)
            self.assertEqual(len(consultation_prescriptions.json()), 1)

            consultation_workflow = await client.get(
                f"/api/v1/order-workflow?patient_id={patient_create.json()['id']}&event_type=consultation_order_created",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(consultation_workflow.status_code, 200, consultation_workflow.text)
            self.assertTrue(
                {"lab", "radiology", "prescription"}.issubset(
                    {event["order_type"] for event in consultation_workflow.json()}
                )
            )

            consultation_complete = await client.post(
                f"/api/v1/consultations/{consultation_start.json()['id']}/complete",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(consultation_complete.status_code, 200, consultation_complete.text)
            self.assertEqual(consultation_complete.json()["status"], "completed")
            self.assertEqual(consultation_complete.json()["appointment_status"], "COMPLETED")

            consultation_list = await client.get(
                f"/api/v1/consultations?patient_id={patient_create.json()['id']}",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(consultation_list.status_code, 200, consultation_list.text)
            self.assertGreaterEqual(len(consultation_list.json()), 1)

            queue_create = await client.post(
                "/api/v1/queue",
                json={
                    "patient_id": patient_create.json()["id"],
                    "appointment_id": appointment_create.json()["id"],
                    "department": "Front Desk",
                    "priority": "normal",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:patient-queue",
                },
            )

            self.assertEqual(queue_create.status_code, 201, queue_create.text)
            self.assertEqual(queue_create.json()["queue_number"], 1)
            self.assertEqual(queue_create.json()["patient_name"], "Musa Bello")
            queue_replay = await client.post(
                "/api/v1/queue",
                json={
                    "patient_id": patient_create.json()["id"],
                    "appointment_id": appointment_create.json()["id"],
                    "department": "Front Desk",
                    "priority": "normal",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:patient-queue",
                },
            )
            self.assertEqual(queue_replay.status_code, 200, queue_replay.text)
            self.assertEqual(queue_replay.json()["id"], queue_create.json()["id"])

            queue_list = await client.get(
                "/api/v1/queue",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(queue_list.status_code, 200, queue_list.text)
            self.assertEqual(queue_list.json()["total"], 1)

            ward_bed_create = await client.post(
                "/api/v1/wards/beds",
                json={
                    "ward_name": "Observation Ward",
                    "bed_number": "OBS-01",
                    "notes": "Near nurses station",
                },
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(ward_bed_create.status_code, 201, ward_bed_create.text)
            self.assertEqual(ward_bed_create.json()["status"], "AVAILABLE")
            self.assertEqual(ward_bed_create.json()["bed_number"], "OBS-01")

            ward_admission_create = await client.post(
                "/api/v1/wards/admissions",
                json={
                    "patient_id": patient_create.json()["id"],
                    "bed_id": ward_bed_create.json()["id"],
                    "ward_name": "Observation Ward",
                    "reason": "Short stay clinical observation",
                    "acuity": "urgent",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:ward-admission",
                },
            )

            self.assertEqual(ward_admission_create.status_code, 201, ward_admission_create.text)
            self.assertEqual(ward_admission_create.json()["patient_name"], "Musa Bello")
            self.assertEqual(ward_admission_create.json()["bed_number"], "OBS-01")
            self.assertEqual(ward_admission_create.json()["status"], "ACTIVE")

            ward_admission_replay = await client.post(
                "/api/v1/wards/admissions",
                json={
                    "patient_id": patient_create.json()["id"],
                    "bed_id": ward_bed_create.json()["id"],
                    "ward_name": "Observation Ward",
                    "reason": "Short stay clinical observation",
                    "acuity": "urgent",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:ward-admission",
                },
            )
            self.assertEqual(ward_admission_replay.status_code, 200, ward_admission_replay.text)
            self.assertEqual(ward_admission_replay.json()["id"], ward_admission_create.json()["id"])

            ward_observation = await client.post(
                f"/api/v1/wards/admissions/{ward_admission_create.json()['id']}/observations",
                json={
                    "vital_signs": {"temperature": "37.8", "blood_pressure": "118/76"},
                    "note": "Patient settled in bed and tolerating oral fluids.",
                    "medication_round": "Paracetamol administered",
                },
                headers={
                    "Authorization": f"Bearer {staff_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:ward-observation",
                },
            )

            self.assertEqual(ward_observation.status_code, 200, ward_observation.text)
            self.assertEqual(len(ward_observation.json()["observations"]), 1)
            self.assertEqual(len(ward_observation.json()["nursing_notes"]), 1)

            ward_observation_replay = await client.post(
                f"/api/v1/wards/admissions/{ward_admission_create.json()['id']}/observations",
                json={
                    "vital_signs": {"temperature": "37.8", "blood_pressure": "118/76"},
                    "note": "Patient settled in bed and tolerating oral fluids.",
                    "medication_round": "Paracetamol administered",
                },
                headers={
                    "Authorization": f"Bearer {staff_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:ward-observation",
                },
            )
            self.assertEqual(ward_observation_replay.status_code, 200, ward_observation_replay.text)
            self.assertEqual(len(ward_observation_replay.json()["observations"]), 1)

            active_admissions = await client.get(
                "/api/v1/wards/admissions?status=ACTIVE",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(active_admissions.status_code, 200, active_admissions.text)
            self.assertEqual(len(active_admissions.json()), 1)

            ward_discharge = await client.post(
                f"/api/v1/wards/admissions/{ward_admission_create.json()['id']}/discharge",
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:ward-discharge",
                },
            )

            self.assertEqual(ward_discharge.status_code, 200, ward_discharge.text)
            self.assertEqual(ward_discharge.json()["status"], "DISCHARGED")

            ward_discharge_replay = await client.post(
                f"/api/v1/wards/admissions/{ward_admission_create.json()['id']}/discharge",
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:ward-discharge",
                },
            )
            self.assertEqual(ward_discharge_replay.status_code, 200, ward_discharge_replay.text)
            self.assertEqual(ward_discharge_replay.json()["id"], ward_admission_create.json()["id"])

            discharge_notifications = await client.get(
                f"/api/v1/patient-notifications?patient_id={patient_create.json()['id']}&notification_type=discharge_follow_up",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(discharge_notifications.status_code, 200, discharge_notifications.text)
            self.assertGreaterEqual(len(discharge_notifications.json()), 2)

            ward_beds_after_discharge = await client.get(
                "/api/v1/wards/beds?status=AVAILABLE",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(ward_beds_after_discharge.status_code, 200, ward_beds_after_discharge.text)
            self.assertEqual(ward_beds_after_discharge.json()[0]["bed_number"], "OBS-01")

            invoice_create = await client.post(
                "/api/v1/billing/invoices",
                json={
                    "patient_id": patient_create.json()["id"],
                    "amount": 25000,
                    "due_date": "2026-06-08",
                    "notes": "Initial consultation and registration",
                },
                headers={
                    **billing_headers,
                    "Idempotency-Key": "setup-invoice-create-0001",
                },
            )

            self.assertEqual(invoice_create.status_code, 201, invoice_create.text)
            self.assertEqual(invoice_create.json()["amount"], 25000)
            self.assertEqual(invoice_create.json()["paid_amount"], 0)
            self.assertEqual(invoice_create.json()["balance"], 25000)
            self.assertEqual(invoice_create.json()["status"], "PENDING")
            self.assertEqual(invoice_create.json()["facility_slug"], "sunrise-medical-centre")

            invoice_replay = await client.post(
                "/api/v1/billing/invoices",
                json={
                    "patient_id": patient_create.json()["id"],
                    "amount": 25000,
                    "due_date": "2026-06-08",
                    "notes": "Initial consultation and registration",
                },
                headers={
                    **billing_headers,
                    "Idempotency-Key": "setup-invoice-create-0001",
                },
            )
            self.assertEqual(invoice_replay.status_code, 200, invoice_replay.text)
            self.assertEqual(invoice_replay.json()["id"], invoice_create.json()["id"])

            bill_notifications = await client.get(
                f"/api/v1/patient-notifications?patient_id={patient_create.json()['id']}&notification_type=bill_created",
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                },
            )

            self.assertEqual(bill_notifications.status_code, 200, bill_notifications.text)
            self.assertGreaterEqual(len(bill_notifications.json()), 2)

            payment_create = await client.post(
                f"/api/v1/billing/invoices/{invoice_create.json()['id']}/payments",
                json={
                    "amount": 10000,
                    "payment_method": "CASH",
                    "reference": "RCPT-001",
                    "notes": "Deposit",
                },
                headers={
                    **billing_headers,
                    "Idempotency-Key": "setup-payment-create-0001",
                },
            )

            self.assertEqual(payment_create.status_code, 201, payment_create.text)
            self.assertEqual(payment_create.json()["amount"], 10000)
            self.assertEqual(payment_create.json()["reference"], "RCPT-001")
            self.assertFalse(payment_create.json()["has_receipt"])

            payment_replay = await client.post(
                f"/api/v1/billing/invoices/{invoice_create.json()['id']}/payments",
                json={
                    "amount": 10000,
                    "payment_method": "CASH",
                    "reference": "RCPT-001",
                    "notes": "Deposit",
                },
                headers={
                    **billing_headers,
                    "Idempotency-Key": "setup-payment-create-0001",
                },
            )
            self.assertEqual(payment_replay.status_code, 200, payment_replay.text)
            self.assertEqual(payment_replay.json()["id"], payment_create.json()["id"])

            payment_notifications = await client.get(
                f"/api/v1/patient-notifications?patient_id={patient_create.json()['id']}&notification_type=payment_received",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(payment_notifications.status_code, 200, payment_notifications.text)
            self.assertGreaterEqual(len(payment_notifications.json()), 2)

            invalid_receipt_upload = await client.post(
                f"/api/v1/billing/payments/{payment_create.json()['id']}/receipt",
                files={"file": ("receipt.txt", b"not an image", "text/plain")},
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(invalid_receipt_upload.status_code, 400, invalid_receipt_upload.text)

            oversized_receipt_upload = await client.post(
                f"/api/v1/billing/payments/{payment_create.json()['id']}/receipt",
                files={"file": ("receipt.png", b"\x89PNG\r\n\x1a\n" + b"a" * (5 * 1024 * 1024 + 1), "image/png")},
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(oversized_receipt_upload.status_code, 413, oversized_receipt_upload.text)

            receipt_upload = await client.post(
                f"/api/v1/billing/payments/{payment_create.json()['id']}/receipt",
                files={"file": ("receipt.png", b"\x89PNG\r\n\x1a\nsmall-receipt", "image/png")},
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(receipt_upload.status_code, 200, receipt_upload.text)
            self.assertTrue(receipt_upload.json()["has_receipt"])
            self.assertEqual(receipt_upload.json()["receipt_original_name"], "receipt.png")

            receipt_download = await client.get(
                f"/api/v1/billing/payments/{payment_create.json()['id']}/receipt",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(receipt_download.status_code, 200, receipt_download.text)
            self.assertEqual(receipt_download.headers["content-type"], "image/png")
            self.assertIn(b"small-receipt", receipt_download.content)

            invoice_list = await client.get(
                "/api/v1/billing/invoices",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(invoice_list.status_code, 200, invoice_list.text)
            self.assertEqual(len(invoice_list.json()), 1)
            self.assertEqual(invoice_list.json()[0]["paid_amount"], 10000)
            self.assertEqual(invoice_list.json()[0]["balance"], 15000)
            self.assertEqual(invoice_list.json()[0]["status"], "PARTIAL")

            report_summary = await client.get(
                "/api/v1/reports/summary?date_from=2026-01-01&date_to=2026-12-31",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(report_summary.status_code, 200, report_summary.text)
            self.assertEqual(report_summary.json()["facility_slug"], "sunrise-medical-centre")
            self.assertEqual(report_summary.json()["patients"]["total"], 2)
            self.assertGreaterEqual(report_summary.json()["consultations"]["total"], 2)
            self.assertEqual(report_summary.json()["queue"]["by_status"]["waiting"], 1)
            self.assertEqual(report_summary.json()["admissions"]["by_status"]["DISCHARGED"], 1)
            self.assertEqual(report_summary.json()["billing"]["invoice_count"], 1)
            self.assertEqual(report_summary.json()["billing"]["payments_total"], 10000)
            self.assertEqual(report_summary.json()["billing"]["outstanding_total"], 15000)

            revenue_report = await client.get(
                "/api/v1/reports/revenue?date_from=2026-01-01&date_to=2026-12-31",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(revenue_report.status_code, 200, revenue_report.text)
            self.assertEqual(revenue_report.json()["invoice_count"], 1)
            self.assertEqual(revenue_report.json()["collected_total"], 10000)
            self.assertEqual(revenue_report.json()["outstanding_total"], 15000)
            self.assertEqual(revenue_report.json()["receipt_count"], 1)
            self.assertIn(
                "CASH",
                {row["label"] for row in revenue_report.json()["payment_methods"]},
            )
            self.assertTrue(revenue_report.json()["recent_payments"][0]["metadata"]["has_receipt"])

            department_report = await client.get(
                "/api/v1/reports/departments?date_from=2026-01-01&date_to=2026-12-31",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(department_report.status_code, 200, department_report.text)
            self.assertTrue(
                {
                    "Consultations",
                    "Laboratory",
                    "Radiology",
                    "Pharmacy",
                    "Wards",
                }.issubset(
                    {row["department"] for row in department_report.json()["departments"]}
                )
            )

            operations_report = await client.get(
                "/api/v1/reports/operations?date_from=2026-01-01&date_to=2026-12-31",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(operations_report.status_code, 200, operations_report.text)
            self.assertEqual(operations_report.json()["queue"]["by_status"]["waiting"], 1)
            self.assertIn("active_tasks_by_role", operations_report.json())

            lab_test_create = await client.post(
                "/api/v1/laboratory/tests",
                json={
                    "name": "Full Blood Count",
                    "code": "FBC",
                    "category": "Haematology",
                    "unit": "cells/L",
                    "reference_range": "4.0-11.0",
                    "price": 7500,
                },
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(lab_test_create.status_code, 201, lab_test_create.text)
            self.assertEqual(lab_test_create.json()["code"], "FBC")

            lab_tests = await client.get(
                "/api/v1/laboratory/tests",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(lab_tests.status_code, 200, lab_tests.text)
            self.assertEqual(lab_tests.json()[0]["name"], "Full Blood Count")

            lab_order_create = await client.post(
                "/api/v1/laboratory/orders",
                json={
                    "patient_id": patient_create.json()["id"],
                    "test_id": lab_test_create.json()["id"],
                    "priority": "URGENT",
                    "notes": "Fever workup",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:lab-order",
                },
            )

            self.assertEqual(lab_order_create.status_code, 201, lab_order_create.text)
            self.assertEqual(lab_order_create.json()["status"], "PENDING")
            self.assertEqual(lab_order_create.json()["facility_slug"], "sunrise-medical-centre")
            lab_order_replay = await client.post(
                "/api/v1/laboratory/orders",
                json={
                    "patient_id": patient_create.json()["id"],
                    "test_id": lab_test_create.json()["id"],
                    "priority": "URGENT",
                    "notes": "Fever workup",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:lab-order",
                },
            )
            self.assertEqual(lab_order_replay.status_code, 200, lab_order_replay.text)
            self.assertEqual(lab_order_replay.json()["id"], lab_order_create.json()["id"])

            lab_created_workflow = await client.get(
                f"/api/v1/order-workflow?order_id={lab_order_create.json()['id']}&event_type=consultation_order_created",
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                },
            )

            self.assertEqual(lab_created_workflow.status_code, 200, lab_created_workflow.text)
            self.assertEqual(lab_created_workflow.json()[0]["order_type"], "lab")

            lab_tasks = await client.get(
                "/api/v1/tasks?role=LAB_TECH",
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                },
            )

            self.assertEqual(lab_tasks.status_code, 200, lab_tasks.text)
            self.assertIn(
                "Collect sample",
                {task["title"] for task in lab_tasks.json()["tasks"]},
            )

            lab_order_list = await client.get(
                "/api/v1/laboratory/orders",
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                },
            )

            self.assertEqual(lab_order_list.status_code, 200, lab_order_list.text)
            self.assertGreaterEqual(len(lab_order_list.json()), 2)

            lab_order_update = await client.put(
                f"/api/v1/laboratory/orders/{lab_order_create.json()['id']}",
                json={"status": "COLLECTED"},
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                },
            )

            self.assertEqual(lab_order_update.status_code, 200, lab_order_update.text)
            self.assertEqual(lab_order_update.json()["status"], "COLLECTED")

            sample_collected_workflow = await client.get(
                f"/api/v1/order-workflow?order_id={lab_order_create.json()['id']}&event_type=lab_sample_collected",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(sample_collected_workflow.status_code, 200, sample_collected_workflow.text)
            self.assertEqual(sample_collected_workflow.json()[0]["status"], "COLLECTED")

            lab_result_create = await client.post(
                f"/api/v1/laboratory/results/{lab_order_create.json()['id']}",
                json={
                    "value": "13.4",
                    "is_abnormal": False,
                    "notes": "Within reference range",
                },
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(lab_result_create.status_code, 201, lab_result_create.text)
            self.assertEqual(lab_result_create.json()["value"], "13.4")

            lab_result_lookup = await client.get(
                f"/api/v1/laboratory/results/{lab_order_create.json()['id']}",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(lab_result_lookup.status_code, 200, lab_result_lookup.text)
            self.assertEqual(lab_result_lookup.json()["notes"], "Within reference range")

            lab_result_notifications = await client.get(
                f"/api/v1/patient-notifications?patient_id={patient_create.json()['id']}&notification_type=lab_result_ready",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(lab_result_notifications.status_code, 200, lab_result_notifications.text)
            self.assertGreaterEqual(len(lab_result_notifications.json()), 2)

            lab_result_workflow = await client.get(
                f"/api/v1/order-workflow?order_id={lab_order_create.json()['id']}",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(lab_result_workflow.status_code, 200, lab_result_workflow.text)
            self.assertTrue(
                {"lab_result_released", "doctor_notified"}.issubset(
                    {event["event_type"] for event in lab_result_workflow.json()}
                )
            )

            doctor_notifications = await client.get(
                "/api/v1/alerts?is_read=false&per_page=100",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(doctor_notifications.status_code, 200, doctor_notifications.text)
            self.assertIn(
                "Lab result ready",
                {alert["title"] for alert in doctor_notifications.json()},
            )

            mark_all_notifications_read = await client.put(
                "/api/v1/alerts/actions/mark-all-read",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(mark_all_notifications_read.status_code, 200, mark_all_notifications_read.text)

            radiology_create = await client.post(
                "/api/v1/radiology",
                json={
                    "patient_id": patient_create.json()["id"],
                    "facility_slug": "attacker-supplied-facility",
                    "modality": "X-ray",
                    "body_part": "Chest",
                    "clinical_notes": "Cough and fever",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:radiology-order",
                },
            )

            self.assertEqual(radiology_create.status_code, 201, radiology_create.text)
            self.assertEqual(radiology_create.json()["facility_slug"], "sunrise-medical-centre")
            self.assertEqual(radiology_create.json()["status"], "pending")

            radiology_replay = await client.post(
                "/api/v1/radiology",
                json={
                    "patient_id": patient_create.json()["id"],
                    "facility_slug": "attacker-supplied-facility",
                    "modality": "X-ray",
                    "body_part": "Chest",
                    "clinical_notes": "Cough and fever",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:radiology-order",
                },
            )
            self.assertEqual(radiology_replay.status_code, 200, radiology_replay.text)
            self.assertEqual(radiology_replay.json()["id"], radiology_create.json()["id"])

            radiology_list = await client.get(
                "/api/v1/radiology?per_page=100",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(radiology_list.status_code, 200, radiology_list.text)
            self.assertGreaterEqual(len(radiology_list.json()), 2)
            self.assertTrue(all(order["patient_name"] == "Musa Bello" for order in radiology_list.json()))

            radiology_update = await client.put(
                f"/api/v1/radiology/{radiology_create.json()['id']}",
                json={"status": "ordered"},
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(radiology_update.status_code, 200, radiology_update.text)
            self.assertEqual(radiology_update.json()["status"], "ordered")

            radiology_report = await client.put(
                f"/api/v1/radiology/{radiology_create.json()['id']}/report",
                json={"report": "No acute cardiopulmonary abnormality."},
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(radiology_report.status_code, 200, radiology_report.text)
            self.assertEqual(radiology_report.json()["status"], "completed")
            self.assertEqual(
                radiology_report.json()["report"],
                "No acute cardiopulmonary abnormality.",
            )

            radiology_notifications = await client.get(
                f"/api/v1/patient-notifications?patient_id={patient_create.json()['id']}&notification_type=radiology_report_ready",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(radiology_notifications.status_code, 200, radiology_notifications.text)
            self.assertGreaterEqual(len(radiology_notifications.json()), 2)

            radiology_workflow = await client.get(
                f"/api/v1/order-workflow?order_id={radiology_create.json()['id']}",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(radiology_workflow.status_code, 200, radiology_workflow.text)
            self.assertTrue(
                {"radiology_report_completed", "doctor_notified"}.issubset(
                    {event["event_type"] for event in radiology_workflow.json()}
                )
            )

            medication_create = await client.post(
                "/api/v1/pharmacy/medications",
                json={
                    "name": "Paracetamol",
                    "code": "PCM-500",
                    "generic_name": "Acetaminophen",
                    "category": "Analgesic",
                    "unit": "tablet",
                    "strength": "500mg",
                    "price": 150,
                    "reorder_level": 20,
                },
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(medication_create.status_code, 201, medication_create.text)
            self.assertEqual(medication_create.json()["facility_slug"], "sunrise-medical-centre")

            medication_list = await client.get(
                "/api/v1/pharmacy/medications",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(medication_list.status_code, 200, medication_list.text)
            self.assertGreaterEqual(len(medication_list.json()), 2)
            self.assertIn("PCM-500", {medication["code"] for medication in medication_list.json()})

            inventory_create = await client.post(
                f"/api/v1/pharmacy/inventory/{medication_create.json()['id']}",
                json={
                    "quantity": 50,
                    "expiry_date": "2027-01-31",
                    "batch_number": "BATCH-001",
                    "location": "Main shelf",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:pharmacy-stock-receipt",
                },
            )

            self.assertEqual(inventory_create.status_code, 201, inventory_create.text)
            self.assertEqual(inventory_create.json()["quantity"], 50)

            inventory_create_replay = await client.post(
                f"/api/v1/pharmacy/inventory/{medication_create.json()['id']}",
                json={
                    "quantity": 50,
                    "expiry_date": "2027-01-31",
                    "batch_number": "BATCH-001",
                    "location": "Main shelf",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:pharmacy-stock-receipt",
                },
            )
            self.assertEqual(inventory_create_replay.status_code, 200, inventory_create_replay.text)
            self.assertEqual(inventory_create_replay.json()["quantity"], 50)

            prescription_create = await client.post(
                "/api/v1/pharmacy/prescriptions",
                json={
                    "patient_id": patient_create.json()["id"],
                    "items": [
                        {
                            "medication_id": medication_create.json()["id"],
                            "quantity": 10,
                            "dosage": "1 tablet twice daily",
                            "instructions": "After meals",
                        }
                    ],
                    "notes": "Fever management",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:prescription",
                },
            )

            self.assertEqual(prescription_create.status_code, 201, prescription_create.text)
            self.assertEqual(prescription_create.json()["status"], "PENDING")
            self.assertEqual(prescription_create.json()["facility_slug"], "sunrise-medical-centre")
            prescription_replay = await client.post(
                "/api/v1/pharmacy/prescriptions",
                json={
                    "patient_id": patient_create.json()["id"],
                    "items": [
                        {
                            "medication_id": medication_create.json()["id"],
                            "quantity": 10,
                            "dosage": "1 tablet twice daily",
                            "instructions": "After meals",
                        }
                    ],
                    "notes": "Fever management",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:prescription",
                },
            )
            self.assertEqual(prescription_replay.status_code, 200, prescription_replay.text)
            self.assertEqual(prescription_replay.json()["id"], prescription_create.json()["id"])

            prescription_created_workflow = await client.get(
                f"/api/v1/order-workflow?order_id={prescription_create.json()['id']}&event_type=consultation_order_created",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(prescription_created_workflow.status_code, 200, prescription_created_workflow.text)
            self.assertEqual(prescription_created_workflow.json()[0]["order_type"], "prescription")

            pharmacy_tasks = await client.get(
                "/api/v1/tasks?role=PHARMACIST",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(pharmacy_tasks.status_code, 200, pharmacy_tasks.text)
            self.assertIn(
                "Dispense prescription",
                {task["title"] for task in pharmacy_tasks.json()["tasks"]},
            )

            prescription_dispense = await client.post(
                f"/api/v1/pharmacy/prescriptions/{prescription_create.json()['id']}/dispense",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(prescription_dispense.status_code, 200, prescription_dispense.text)
            self.assertEqual(prescription_dispense.json()["status"], "DISPENSED")

            prescription_notifications = await client.get(
                f"/api/v1/patient-notifications?patient_id={patient_create.json()['id']}&notification_type=prescription_dispensed",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(prescription_notifications.status_code, 200, prescription_notifications.text)
            self.assertGreaterEqual(len(prescription_notifications.json()), 2)

            prescription_workflow = await client.get(
                f"/api/v1/order-workflow?order_id={prescription_create.json()['id']}",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(prescription_workflow.status_code, 200, prescription_workflow.text)
            self.assertTrue(
                {"prescription_dispensed", "doctor_notified"}.issubset(
                    {event["event_type"] for event in prescription_workflow.json()}
                )
            )

            inventory_after_dispense = await client.get(
                f"/api/v1/pharmacy/inventory/{medication_create.json()['id']}",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(inventory_after_dispense.status_code, 200, inventory_after_dispense.text)
            self.assertEqual(inventory_after_dispense.json()["quantity"], 40)

            supplier_create = await client.post(
                "/api/v1/suppliers",
                json={
                    "name": "MedSupply Nigeria",
                    "contact_person": "Kemi Ade",
                    "email": "orders@medsupply.example.com",
                    "phone": "+234 800 777 8888",
                    "address": "Supplier Avenue",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:supplier-create",
                },
            )

            self.assertEqual(supplier_create.status_code, 201, supplier_create.text)
            self.assertEqual(supplier_create.json()["facility_slug"], "sunrise-medical-centre")

            supplier_replay = await client.post(
                "/api/v1/suppliers",
                json={
                    "name": "MedSupply Nigeria",
                    "contact_person": "Kemi Ade",
                    "email": "orders@medsupply.example.com",
                    "phone": "+234 800 777 8888",
                    "address": "Supplier Avenue",
                },
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:supplier-create",
                },
            )
            self.assertEqual(supplier_replay.status_code, 200, supplier_replay.text)
            self.assertEqual(supplier_replay.json()["id"], supplier_create.json()["id"])

            supplier_list = await client.get(
                "/api/v1/suppliers",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(supplier_list.status_code, 200, supplier_list.text)
            self.assertEqual(len(supplier_list.json()), 1)

            inventory_item_create = await client.post(
                "/api/v1/inventory",
                json={
                    "facility_slug": "attacker-supplied-facility",
                    "name": "Sterile Gloves",
                    "sku": "GLV-001",
                    "category": "supplies",
                    "unit": "box",
                    "reorder_level": 10,
                    "reorder_quantity": 25,
                    "current_stock": 8,
                    "supplier_id": supplier_create.json()["id"],
                    "unit_cost": 3500,
                },
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(inventory_item_create.status_code, 201, inventory_item_create.text)
            self.assertEqual(inventory_item_create.json()["facility_slug"], "sunrise-medical-centre")
            self.assertEqual(inventory_item_create.json()["supplier_name"], "MedSupply Nigeria")
            self.assertTrue(inventory_item_create.json()["needs_reorder"])

            inventory_list = await client.get(
                "/api/v1/inventory?per_page=100",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(inventory_list.status_code, 200, inventory_list.text)
            self.assertEqual(len(inventory_list.json()), 1)

            low_stock = await client.get(
                "/api/v1/inventory/low-stock",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(low_stock.status_code, 200, low_stock.text)
            self.assertEqual(low_stock.json()[0]["medication_name"], "Sterile Gloves")

            inventory_report = await client.get(
                "/api/v1/reports/inventory",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(inventory_report.status_code, 200, inventory_report.text)
            self.assertEqual(inventory_report.json()["active_items"], 1)
            self.assertEqual(inventory_report.json()["low_stock_items"], 1)
            self.assertEqual(inventory_report.json()["stock_value"], 28000)
            self.assertEqual(inventory_report.json()["reorder_items"][0]["name"], "Sterile Gloves")

            inventory_stock_update = await client.put(
                f"/api/v1/inventory/{inventory_item_create.json()['id']}/stock",
                json={"adjustment_type": "addition", "current_stock": 10},
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:inventory-stock-update",
                },
            )

            self.assertEqual(inventory_stock_update.status_code, 200, inventory_stock_update.text)
            self.assertEqual(inventory_stock_update.json()["current_stock"], 18)
            self.assertFalse(inventory_stock_update.json()["needs_reorder"])

            inventory_stock_replay = await client.put(
                f"/api/v1/inventory/{inventory_item_create.json()['id']}/stock",
                json={"adjustment_type": "addition", "current_stock": 10},
                headers={
                    "Authorization": f"Bearer {email_login.json()['access_token']}",
                    "Idempotency-Key": "test:setup:inventory-stock-update",
                },
            )
            self.assertEqual(inventory_stock_replay.status_code, 200, inventory_stock_replay.text)
            self.assertEqual(inventory_stock_replay.json()["current_stock"], 18)

            supplier_deactivate = await client.delete(
                f"/api/v1/suppliers/{supplier_create.json()['id']}",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(supplier_deactivate.status_code, 200, supplier_deactivate.text)

            supplier_list_after_deactivate = await client.get(
                "/api/v1/suppliers",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(supplier_list_after_deactivate.status_code, 200, supplier_list_after_deactivate.text)
            self.assertEqual(supplier_list_after_deactivate.json(), [])

            patient_timeline = await client.get(
                f"/api/v1/patients/{patient_create.json()['id']}/timeline",
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(patient_timeline.status_code, 200, patient_timeline.text)
            self.assertEqual(patient_timeline.json()["patient"]["full_name"], "Musa Bello")
            self.assertGreaterEqual(patient_timeline.json()["total"], 10)
            timeline_event_types = {
                event["event_type"] for event in patient_timeline.json()["events"]
            }
            self.assertTrue(
                {
                    "patient_registered",
                    "appointment",
                    "medical_record",
                    "lab_order",
                    "lab_result",
                    "radiology_order",
                    "radiology_report",
                    "prescription",
                    "prescription_dispensed",
                    "invoice",
                    "payment",
                    "patient_notification",
                    "workflow_consultation_order_created",
                    "workflow_lab_sample_collected",
                    "workflow_lab_result_released",
                    "workflow_radiology_report_completed",
                    "workflow_prescription_dispensed",
                    "workflow_doctor_notified",
                    "ward_admission",
                    "ward_discharge",
                }.issubset(timeline_event_types),
                timeline_event_types,
            )
            payment_events = [
                event for event in patient_timeline.json()["events"]
                if event["event_type"] == "payment"
            ]
            self.assertTrue(any(event["metadata"]["has_receipt"] for event in payment_events))

            password_change = await client.post(
                "/api/v1/users/me/change-password",
                json={
                    "current_password": "Sunrise2026",
                    "new_password": "Sunrise2027",
                },
                headers={"Authorization": f"Bearer {email_login.json()['access_token']}"},
            )

            self.assertEqual(password_change.status_code, 200, password_change.text)

            changed_password_login = await client.post(
                "/api/v1/auth/login?facility_slug=sunrise-medical-centre",
                json={
                    "username": "admin@sunrise.example.com",
                    "password": "Sunrise2027",
                },
            )

            self.assertEqual(changed_password_login.status_code, 200, changed_password_login.text)

            from app.services.tenant_service import TENANT_SCOPED_MODELS

            for model in TENANT_SCOPED_MODELS:
                missing_tenant_id = (
                    self.db_session.query(model)
                    .filter(
                        model.facility_slug == "sunrise-medical-centre",
                        model.facility_id.is_(None),
                    )
                    .count()
                )
                self.assertEqual(
                    missing_tenant_id,
                    0,
                    f"{model.__name__} rows must carry facility_id tenant key",
                )

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
