from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from archive_workbench_ai.handoff import inspect_handoff_bundle


class HandoffTests(unittest.TestCase):
    def test_handoff_builds_proposed_only_bundle_with_traceable_page(self) -> None:
        root = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as name:
            work = Path(name)
            job = work / "job"
            subprocess.run([sys.executable, str(root / "scripts" / "make_demo_job.py"), "--output", str(job)], check=True)
            result = work / "result.zip"
            run = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "archive_workbench_ai.cli",
                    "run",
                    "--request",
                    str(job / "request.json"),
                    "--input",
                    str(job / "exp01.zip"),
                    "--output",
                    str(result),
                    "--backend",
                    "mock",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(run.returncode, 0, run.stderr)

            handoff = work / "handoff.zip"
            built = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "archive_workbench_ai.cli",
                    "handoff",
                    "build",
                    "--input",
                    str(job / "exp01.zip"),
                    "--result",
                    str(result),
                    "--output",
                    str(handoff),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(built.returncode, 0, built.stderr)
            payload = json.loads(built.stdout)
            self.assertEqual(payload["proposal_count"], 1)
            self.assertFalse(payload["automatic_apply"])

            inspected = inspect_handoff_bundle(handoff)
            self.assertEqual(inspected["status"], "ok")
            self.assertEqual(inspected["proposal_count"], 1)
            self.assertFalse(inspected["policy"]["automatic_apply"])

            with zipfile.ZipFile(handoff) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                row = json.loads(archive.read("results/proposals.jsonl").decode("utf-8").strip())
                self.assertEqual(manifest["package_type"], "archive_workbench_ai_result_handoff")
                self.assertEqual(manifest["schema_version"], "0.1")
                self.assertEqual(manifest["policy"]["application"], "proposed_only")
                self.assertIn("exp01_sha256", row["provenance"])
                self.assertIn("result_bundle_sha256", row["provenance"])
                self.assertEqual(row["target_id"], "page:demo:1")
                self.assertIn("original_filename", row)

    def test_handoff_rejects_result_from_different_exp01(self) -> None:
        root = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as name:
            work = Path(name)
            job_a = work / "a"
            job_b = work / "b"
            subprocess.run([sys.executable, str(root / "scripts" / "make_demo_job.py"), "--output", str(job_a)], check=True)
            subprocess.run([sys.executable, str(root / "scripts" / "make_demo_job.py"), "--output", str(job_b)], check=True)
            # Force different EXP-01 bytes while keeping valid ZIP structure.
            with zipfile.ZipFile(job_b / "exp01.zip", "a") as archive:
                archive.writestr("extra.txt", "different")
            result = work / "result.zip"
            run = subprocess.run(
                [sys.executable, "-m", "archive_workbench_ai.cli", "run", "--request", str(job_a / "request.json"), "--input", str(job_a / "exp01.zip"), "--output", str(result), "--backend", "mock"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            handoff = work / "handoff.zip"
            built = subprocess.run(
                [sys.executable, "-m", "archive_workbench_ai.cli", "handoff", "build", "--input", str(job_b / "exp01.zip"), "--result", str(result), "--output", str(handoff)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(built.returncode, 0)
            self.assertIn("no corresponde", built.stderr)


if __name__ == "__main__":
    unittest.main()
