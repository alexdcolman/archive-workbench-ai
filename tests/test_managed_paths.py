from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import archive_workbench_ai.managed_paths as managed


class ManagedPathsTests(unittest.TestCase):
    def test_bridge_root_lives_under_data_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"AW_AI_DATA_HOME": tmp}, clear=False):
                self.assertEqual(managed.default_bridge_root(), Path(tmp).resolve() / "bridge")

    def test_linux_managed_executable_is_stable_per_user(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "data"
            with mock.patch.object(managed.os, "name", "posix"), mock.patch.object(managed.sys, "platform", "linux"), mock.patch.dict(os.environ, {"XDG_DATA_HOME": str(base)}, clear=False):
                candidates = managed.managed_executable_candidates()
            self.assertEqual(
                candidates,
                (
                    Path("/opt/archive-workbench-ai/aw-ai"),
                    base / "archive-workbench-ai" / "app" / "aw-ai",
                ),
            )


if __name__ == "__main__":
    unittest.main()
