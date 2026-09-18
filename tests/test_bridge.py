from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import uuid

from archive_workbench_ai.bridge import (
    BRIDGE_PROTOCOL,
    bridge_capabilities,
    initialize_bridge,
    process_job,
    process_pending,
)
from archive_workbench_ai.errors import InvalidInputError


class BridgeTests(unittest.TestCase):
    def _job(self, root: Path, *, authorization: str | None = None) -> Path:
        initialize_bridge(root)
        secret = (root / "secret.token").read_text(encoding="utf-8").strip()
        job_id = str(uuid.uuid4())
        job = root / "jobs" / job_id
        job.mkdir(parents=True)
        payload = b"EXP01-BRIDGE"
        (job / "input.exp01.zip").write_bytes(payload)
        request = {
            "bridge_protocol": BRIDGE_PROTOCOL,
            "job_id": job_id,
            "authorization": authorization if authorization is not None else secret,
            "created_at": "2026-09-18T12:00:00Z",
            "hardware_profile": "H24",
            "model_id": "ggml-org/gemma-4-26B-A4B-it-GGUF:Q4_0",
            "target_types": ["page"],
            "max_output_tokens": 512,
            "temperature": 0.0,
            "seed": 0,
            "input_sha256": hashlib.sha256(payload).hexdigest(),
        }
        (job / "request.json").write_text(json.dumps(request), encoding="utf-8")
        (job / "ready").write_text("ready\n", encoding="utf-8")
        return job

    def test_initialize_creates_private_secret_and_public_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "bridge"
            report = initialize_bridge(root)
            self.assertEqual(report["protocol"], BRIDGE_PROTOCOL)
            self.assertTrue((root / "secret.token").is_file())
            caps = json.loads((root / "capabilities.json").read_text(encoding="utf-8"))
            self.assertEqual(caps["bridge_protocol"], BRIDGE_PROTOCOL)
            self.assertEqual(caps["plugin"], "archive-workbench-ai")
            self.assertNotIn("authorization", caps)

    def test_invalid_authorization_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "bridge"
            job = self._job(root, authorization="wrong-token")
            with self.assertRaises(InvalidInputError):
                process_job(job)

    def test_process_job_uses_fixed_files_and_writes_consolidated_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "bridge"
            job = self._job(root)

            def fake_analyze(**kwargs):
                self.assertEqual(kwargs["input_path"], job / "input.exp01.zip")
                self.assertEqual(kwargs["handoff_output_path"], job / "handoff.zip")
                self.assertEqual(kwargs["result_output_path"], job / "result.zip")
                self.assertEqual(kwargs["hardware_profile"], "H24")
                self.assertEqual(kwargs["target_types"], ("page",))
                kwargs["handoff_output_path"].write_bytes(b"handoff")
                kwargs["result_output_path"].write_bytes(b"result")
                return {
                    "analysis_id": "analysis-1",
                    "handoff_sha256": hashlib.sha256(b"handoff").hexdigest(),
                    "result_sha256": hashlib.sha256(b"result").hexdigest(),
                    "model_id": kwargs["model_spec"].model_id,
                    "target_count": 5,
                    "proposal_count": 5,
                    "internal_request_count": 2,
                    "handoff_schema_version": "0.1",
                }

            with mock.patch("archive_workbench_ai.bridge.analyze_exp01", side_effect=fake_analyze):
                response = process_job(job)

            self.assertEqual(response["status"], "ok")
            self.assertEqual(response["proposal_count"], 5)
            self.assertEqual(response["internal_request_count"], 2)
            self.assertTrue((job / "result.zip").is_file())
            self.assertTrue((job / "handoff.zip").is_file())

    def test_pending_jobs_are_sequential_and_failures_are_materialized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "bridge"
            first = self._job(root)
            second = self._job(root, authorization="invalid")

            def fake_analyze(**kwargs):
                kwargs["handoff_output_path"].write_bytes(b"handoff")
                kwargs["result_output_path"].write_bytes(b"result")
                return {
                    "analysis_id": "analysis-1",
                    "handoff_sha256": hashlib.sha256(b"handoff").hexdigest(),
                    "result_sha256": hashlib.sha256(b"result").hexdigest(),
                    "model_id": kwargs["model_spec"].model_id,
                    "target_count": 1,
                    "proposal_count": 1,
                    "internal_request_count": 1,
                    "handoff_schema_version": "0.1",
                }

            with mock.patch("archive_workbench_ai.bridge.analyze_exp01", side_effect=fake_analyze):
                self.assertEqual(process_pending(root), 2)
            responses = [json.loads((job / "response.json").read_text(encoding="utf-8")) for job in (first, second)]
            self.assertEqual(sorted(item["status"] for item in responses), ["error", "ok"])

    def test_capabilities_expose_bridge_without_changing_file_contracts(self) -> None:
        caps = bridge_capabilities()
        self.assertEqual(caps["bridge_protocol"], BRIDGE_PROTOCOL)
        self.assertIn("archive-workbench-ai/0.1", caps["protocols"])
        self.assertIn("archive_workbench_ai_result_handoff/0.1", caps["handoff_schema_ids"])


if __name__ == "__main__":
    unittest.main()
