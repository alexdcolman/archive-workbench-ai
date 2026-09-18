from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
