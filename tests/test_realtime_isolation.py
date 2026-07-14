import os
import sys
import unittest
import asyncio
from pathlib import Path
from types import SimpleNamespace


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.routes.realtime import (
    _allowed_websocket_origins,
    _connections_by_facility,
    _connections_by_user,
    _try_register_connection,
    _unregister_connection,
)
from app.services.realtime_service import (
    RealtimeBroker,
    build_realtime_event,
    event_visible_to_user,
    public_realtime_event,
)


class RealtimeIsolationTest(unittest.TestCase):
    def test_realtime_event_visibility_is_tenant_branch_user_and_role_scoped(self):
        doctor = SimpleNamespace(
            id="doctor-1",
            facility_slug="alpha-hospital",
            role="DOCTOR",
            branch_id="branch-a",
            department_id=None,
            branch_ids=[],
            departments=[],
        )
        other_branch_doctor = SimpleNamespace(
            id="doctor-2",
            facility_slug="alpha-hospital",
            role="DOCTOR",
            branch_id="branch-b",
            department_id=None,
            branch_ids=[],
            departments=[],
        )
        other_facility_doctor = SimpleNamespace(
            id="doctor-3",
            facility_slug="beta-hospital",
            role="DOCTOR",
            branch_id="branch-a",
            department_id=None,
            branch_ids=[],
            departments=[],
        )
        receptionist = SimpleNamespace(
            id="reception-1",
            facility_slug="alpha-hospital",
            role="RECEPTIONIST",
            branch_id="branch-a",
            department_id=None,
            branch_ids=[],
            departments=[],
        )

        event = build_realtime_event(
            event_type="lab_result.released",
            facility_slug="alpha-hospital",
            branch_id="branch-a",
            user_id="doctor-1",
            roles=["DOCTOR"],
            modules=["lab", "records"],
            resource_id="order-1",
        )

        self.assertTrue(event_visible_to_user(event, doctor))
        self.assertFalse(event_visible_to_user(event, other_branch_doctor))
        self.assertFalse(event_visible_to_user(event, other_facility_doctor))
        self.assertFalse(event_visible_to_user(event, receptionist))

    def test_admin_can_receive_branch_scoped_facility_event(self):
        admin = SimpleNamespace(
            id="admin-1",
            facility_slug="alpha-hospital",
            role="ADMIN",
            branch_id=None,
            department_id=None,
            branch_ids=[],
            departments=[],
        )
        event = build_realtime_event(
            event_type="queue.updated",
            facility_slug="alpha-hospital",
            branch_id="branch-a",
            roles=["ADMIN", "RECEPTIONIST"],
        )

        self.assertTrue(event_visible_to_user(event, admin))

    def test_websocket_origin_allowlist_uses_configured_origins(self):
        previous = os.environ.get("ALLOWED_ORIGINS")
        try:
            os.environ["ALLOWED_ORIGINS"] = "https://hospital.example, https://admin.example/"
            origins = _allowed_websocket_origins()
            self.assertIn("https://hospital.example", origins)
            self.assertIn("https://admin.example", origins)
        finally:
            if previous is None:
                os.environ.pop("ALLOWED_ORIGINS", None)
            else:
                os.environ["ALLOWED_ORIGINS"] = previous

    def test_public_event_strips_private_routing_fields(self):
        event = build_realtime_event(
            event_type="alert.created",
            facility_slug="alpha-hospital",
            user_id="user-1",
            roles=["DOCTOR"],
            resource_id="alert-1",
        )

        public_event = public_realtime_event(event)

        self.assertEqual(public_event["facility_slug"], "alpha-hospital")
        self.assertEqual(public_event["resource_id"], "alert-1")
        self.assertNotIn("user_id", public_event)
        self.assertNotIn("roles", public_event)

    def test_realtime_connection_limit_is_enforced_and_released(self):
        previous = os.environ.get("REALTIME_MAX_CONNECTIONS_PER_USER")
        user = SimpleNamespace(id="user-limit", facility_slug="alpha-hospital")
        try:
            os.environ["REALTIME_MAX_CONNECTIONS_PER_USER"] = "1"
            _connections_by_user.clear()
            _connections_by_facility.clear()

            self.assertTrue(_try_register_connection(user))
            self.assertFalse(_try_register_connection(user))

            _unregister_connection(user)
            self.assertTrue(_try_register_connection(user))
        finally:
            _connections_by_user.clear()
            _connections_by_facility.clear()
            if previous is None:
                os.environ.pop("REALTIME_MAX_CONNECTIONS_PER_USER", None)
            else:
                os.environ["REALTIME_MAX_CONNECTIONS_PER_USER"] = previous

    def test_realtime_broker_close_clears_subscribers_and_can_be_reused(self):
        async def run_test():
            broker = RealtimeBroker()
            first_queue = await broker.subscribe("alpha-hospital")
            await broker.publish(build_realtime_event(event_type="patient.created", facility_slug="alpha-hospital"))
            self.assertEqual((await first_queue.get())["type"], "patient.created")

            await broker.close()

            second_queue = await broker.subscribe("alpha-hospital")
            await broker.publish(build_realtime_event(event_type="patient.updated", facility_slug="alpha-hospital"))
            self.assertEqual((await second_queue.get())["type"], "patient.updated")
            await broker.close()

        previous = os.environ.get("REDIS_URL")
        try:
            os.environ.pop("REDIS_URL", None)
            asyncio.run(run_test())
        finally:
            if previous is not None:
                os.environ["REDIS_URL"] = previous


if __name__ == "__main__":
    unittest.main()
