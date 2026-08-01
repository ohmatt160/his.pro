import os
import unittest
from unittest.mock import Mock, patch

from scripts import start_service


class StartServiceTests(unittest.TestCase):
    def test_gunicorn_command_uses_configured_port_and_worker_count(self):
        with patch.dict(
            os.environ,
            {"PORT": "9000", "WEB_CONCURRENCY": "4"},
            clear=False,
        ):
            command = start_service._gunicorn_command()

        self.assertIn("0.0.0.0:9000", command)
        self.assertEqual(command[command.index("--workers") + 1], "4")
        self.assertEqual(command[-1], "app.main:app")

    def test_single_container_mode_runs_migrations_worker_and_web(self):
        worker = Mock()
        worker.poll.return_value = None
        web = Mock()
        web.poll.return_value = 0

        def start_process(_command, label):
            process = worker if label == "background worker" else web
            start_service._processes.append(process)
            return process

        with patch.dict(
            os.environ,
            {
                "RUN_MIGRATIONS_ON_START": "true",
                "BUNDLED_BACKGROUND_WORKER": "true",
            },
            clear=False,
        ), patch.object(start_service, "_run_migrations") as migrations, patch.object(
            start_service,
            "_start_process",
            side_effect=start_process,
        ) as starter, patch.object(start_service, "_stop_process") as stopper, patch.object(
            start_service.signal,
            "signal",
        ):
            result = start_service.main()

        self.assertEqual(result, 0)
        migrations.assert_called_once_with()
        self.assertEqual(starter.call_count, 2)
        self.assertEqual(stopper.call_count, 2)

    def test_worker_exit_stops_the_service(self):
        worker = Mock()
        worker.poll.return_value = 7
        web = Mock()
        web.poll.return_value = None

        def start_process(_command, label):
            process = worker if label == "background worker" else web
            start_service._processes.append(process)
            return process

        with patch.dict(
            os.environ,
            {
                "RUN_MIGRATIONS_ON_START": "false",
                "BUNDLED_BACKGROUND_WORKER": "true",
            },
            clear=False,
        ), patch.object(
            start_service,
            "_start_process",
            side_effect=start_process,
        ), patch.object(start_service, "_stop_process"), patch.object(
            start_service.signal,
            "signal",
        ):
            result = start_service.main()

        self.assertEqual(result, 7)


if __name__ == "__main__":
    unittest.main()
