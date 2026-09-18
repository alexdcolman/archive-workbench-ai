from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

from archive_workbench_ai.errors import IncompatibleProtocolError, InvalidRequestError
from archive_workbench_ai.protocol import load_request


class ProtocolTests(unittest.TestCase):
    def _payload(self) -> dict:
        return {
            "protocol": "archive-workbench-ai/0.1",
            "request_id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "task": {"id": "vision_describe", "version": "0.1"},
            "input": {"bundle_type": "exp01", "sha256": hashlib.sha256(b"x").hexdigest()},
            "targets": [{"target_id": "page:x:1", "target_type": "page"}],
            "execution": {"network_policy": "offline_required", "hardware_profile": "auto", "seed": 0},
            "generation": {"max_output_tokens": 64, "temperature": 0.0},
            "output": {"schema_id": "vision_describe/0.1"},
        }

    def _load(self, payload: dict):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "request.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return load_request(path)

    def test_accepts_minimal_request(self) -> None:
        request = self._load(self._payload())
        self.assertEqual(request.hardware_profile, "auto")
        self.assertEqual(len(request.targets), 1)

    def test_rejects_unknown_protocol(self) -> None:
        payload = self._payload()
        payload["protocol"] = "archive-workbench-ai/9.9"
        with self.assertRaises(IncompatibleProtocolError):
            self._load(payload)

    def test_rejects_extra_fields(self) -> None:
        payload = self._payload()
        payload["surprise"] = True
        with self.assertRaises(InvalidRequestError):
            self._load(payload)


    def test_capabilities_distinguish_bootstrap_from_profile_defaults(self) -> None:
        from archive_workbench_ai.cli import _capabilities

        payload = _capabilities()
        self.assertEqual(payload["plugin"], "archive-workbench-ai")
        self.assertEqual(payload["default_model_role"], "bootstrap_baseline")
        self.assertEqual(
            payload["profile_default_models"]["L12"],
            "unsloth/Qwen3.5-9B-GGUF:Q4_K_M",
        )
        self.assertEqual(
            payload["profile_default_models"]["H24"],
            "ggml-org/gemma-4-26B-A4B-it-GGUF:Q4_0",
        )


if __name__ == "__main__":
    unittest.main()
