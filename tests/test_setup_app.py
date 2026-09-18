from __future__ import annotations

import time
import unittest
from unittest import mock

from archive_workbench_ai.setup_app import SetupOperation, _suggested_profile, setup_status


class SetupAppTests(unittest.TestCase):
    def test_suggested_profile_uses_h24_only_for_large_nvidia_memory(self) -> None:
        self.assertEqual(_suggested_profile([]), "L12")
        self.assertEqual(_suggested_profile([{"memory_total_mib": 12288}]), "L12")
        self.assertEqual(_suggested_profile([{"memory_total_mib": 24576}]), "H24")

    def test_setup_status_is_read_only_and_reports_managed_components(self) -> None:
        fake_runtime = {"installed": True, "recommended_variant": "cpu"}
        fake_model = {"installed": True, "model_id": "model"}
        fake_bridge = {"running": True}
        with (
            mock.patch("archive_workbench_ai.setup_app.gpu_info", return_value=[]),
            mock.patch("archive_workbench_ai.setup_app.runtime_installation_report", return_value=fake_runtime),
            mock.patch("archive_workbench_ai.setup_app.inspect_model", return_value=fake_model),
            mock.patch("archive_workbench_ai.setup_app.bridge_status", return_value=fake_bridge),
            mock.patch("archive_workbench_ai.setup_app._data_root_free_bytes", return_value=123),
        ):
            payload = setup_status()
        self.assertEqual(payload["runtime"], fake_runtime)
        self.assertEqual(payload["bridge"], fake_bridge)
        self.assertEqual(payload["free_bytes"], 123)
        self.assertEqual(set(payload["models"]), {"L12", "H24"})
        self.assertTrue(payload["network_required_for_setup"])
        self.assertFalse(payload["network_required_for_inference"])

    def test_prepare_profile_runs_runtime_model_and_bridge_in_order(self) -> None:
        operation = SetupOperation()
        calls: list[str] = []

        def runtime(*, variant: str, force: bool, allow_source_build: bool):
            calls.append(f"runtime:{variant}:{force}:{allow_source_build}")
            return {}

        def model(_spec):
            calls.append("model")
            return {}

        def bridge(_root):
            calls.append("bridge")
            return {}

        with (
            mock.patch("archive_workbench_ai.setup_app.install_runtime", side_effect=runtime),
            mock.patch("archive_workbench_ai.setup_app.pull_model", side_effect=model),
            mock.patch("archive_workbench_ai.setup_app.start_bridge", side_effect=bridge),
        ):
            self.assertTrue(operation.start("prepare_profile", "L12"))
            deadline = time.monotonic() + 3
            while operation.payload()["state"] == "running" and time.monotonic() < deadline:
                time.sleep(0.01)
        self.assertEqual(operation.payload()["state"], "complete")
        self.assertEqual(calls, ["runtime:auto:False:False", "model", "bridge"])

    def test_second_operation_is_rejected_while_one_is_running(self) -> None:
        operation = SetupOperation()
        blocker = mock.Mock()
        blocker.side_effect = lambda **_kwargs: time.sleep(0.15)
        with mock.patch("archive_workbench_ai.setup_app.install_runtime", blocker):
            self.assertTrue(operation.start("install_runtime"))
            self.assertFalse(operation.start("install_runtime"))
            deadline = time.monotonic() + 2
            while operation.payload()["state"] == "running" and time.monotonic() < deadline:
                time.sleep(0.01)
        self.assertEqual(operation.payload()["state"], "complete")

    def test_operation_error_is_materialized_for_the_ui(self) -> None:
        operation = SetupOperation()
        with mock.patch(
            "archive_workbench_ai.setup_app.install_runtime",
            side_effect=RuntimeError("fallo controlado"),
        ):
            self.assertTrue(operation.start("install_runtime"))
            deadline = time.monotonic() + 2
            while operation.payload()["state"] == "running" and time.monotonic() < deadline:
                time.sleep(0.01)
        payload = operation.payload()
        self.assertEqual(payload["state"], "error")
        self.assertIn("fallo controlado", payload["error"])


if __name__ == "__main__":
    unittest.main()
