from __future__ import annotations

import subprocess
import unittest
from unittest import mock

import archive_workbench_ai.runtime as runtime
from archive_workbench_ai.runtime import _parse_build, _validation_status


class RuntimeParsingTests(unittest.TestCase):
    def test_current_llama_cpp_semver_does_not_masquerade_as_release_build(self) -> None:
        text = "version: 0.4.0-dev (build 1, commit 481c65f)\nbuilt with GNU 13.3.0 for Linux x86_64"
        build, revision = _parse_build(text)
        self.assertIsNone(build)
        self.assertEqual(revision, "481c65f")
        self.assertEqual(_validation_status(build, revision), "pinned")

    def test_release_shaped_build_numbers_are_still_compared(self) -> None:
        self.assertEqual(_parse_build("llama.cpp b10903 (481c65f)")[0], 10903)
        self.assertEqual(_validation_status(10902, "deadbee"), "too_old")
        self.assertEqual(_validation_status(10903, "deadbee"), "pinned")
        self.assertEqual(_validation_status(10904, "deadbee"), "newer_unverified")

    def test_nonzero_version_probe_is_not_available(self) -> None:
        failed = subprocess.CompletedProcess(
            args=["/managed/llama-server", "--version"],
            returncode=127,
            stdout="",
            stderr="error while loading shared libraries: libnccl.so.2: cannot open shared object file",
        )
        with (
            mock.patch.dict("os.environ", {}, clear=True),
            mock.patch("archive_workbench_ai.runtime_manager.managed_runtime_executable", return_value=runtime.Path("/managed/llama-server")),
            mock.patch.object(runtime.shutil, "which", return_value=None),
            mock.patch.object(runtime.subprocess, "run", return_value=failed),
        ):
            detection = runtime.detect_runtime_detailed()
        self.assertIsNone(detection.runtime)
        self.assertEqual(len(detection.failures), 1)
        self.assertEqual(detection.failures[0].returncode, 127)
        self.assertIn("libnccl.so.2", detection.failures[0].detail)

    def test_runtime_detection_skips_broken_candidate_and_uses_healthy_fallback(self) -> None:
        broken = subprocess.CompletedProcess(
            args=["/managed/llama-server", "--version"],
            returncode=127,
            stdout="",
            stderr="missing shared library",
        )
        healthy = subprocess.CompletedProcess(
            args=["/usr/bin/llama-server", "--version"],
            returncode=0,
            stdout="llama.cpp b10903 (481c65f)",
            stderr="",
        )
        def fake_run(argv, **_kwargs):
            return broken if argv[0] == "/managed/llama-server" else healthy
        def fake_which(name):
            return "/usr/bin/llama-server" if name == "llama-server" else None
        with (
            mock.patch.dict("os.environ", {}, clear=True),
            mock.patch("archive_workbench_ai.runtime_manager.managed_runtime_executable", return_value=runtime.Path("/managed/llama-server")),
            mock.patch.object(runtime.shutil, "which", side_effect=fake_which),
            mock.patch.object(runtime.subprocess, "run", side_effect=fake_run),
        ):
            detection = runtime.detect_runtime_detailed()
        self.assertIsNotNone(detection.runtime)
        assert detection.runtime is not None
        self.assertEqual(detection.runtime.executable, "/usr/bin/llama-server")
        self.assertEqual(detection.runtime.status, "pinned")
        self.assertEqual(len(detection.failures), 1)

    def test_runtime_payload_reports_probe_failure_and_doctor_requires_setup(self) -> None:
        from archive_workbench_ai import cli

        failure = runtime.RuntimeProbeFailure(
            executable="/managed/llama-server",
            mode="llama-server",
            returncode=127,
            detail="error while loading shared libraries: libnccl.so.2",
        )
        detection = runtime.RuntimeDetection(runtime=None, failures=(failure,))
        with mock.patch.object(cli, "detect_runtime_detailed", return_value=detection):
            payload = cli._runtime_payload()
        self.assertFalse(payload["available"])
        self.assertEqual(payload["probe_failures"][0]["returncode"], 127)
        self.assertIn("libnccl.so.2", payload["probe_failures"][0]["detail"])

        with (
            mock.patch.object(cli, "_runtime_payload", return_value=payload),
            mock.patch.object(cli, "_models_payload", return_value=[{"model_id": "demo", "installed": True}]),
            mock.patch.object(cli, "gpu_info", return_value=[]),
        ):
            doctor = cli._doctor()
        self.assertEqual(doctor["status"], "setup_required")
        self.assertFalse(doctor["backends"]["llama_cpp"]["available"])


if __name__ == "__main__":
    unittest.main()
