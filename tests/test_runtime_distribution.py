from __future__ import annotations

import json
from pathlib import Path
import io
import tarfile
import zipfile
import tempfile
import unittest
from unittest import mock

import archive_workbench_ai.runtime_manager as manager
from archive_workbench_ai.errors import InvalidInputError
from archive_workbench_ai.runtime_manager import _extract
from archive_workbench_ai.runtime_catalog import PINNED_LLAMA_COMMIT, PINNED_LLAMA_TAG, runtime_package


class RuntimeDistributionTests(unittest.TestCase):
    def test_runtime_catalog_covers_public_release_targets(self) -> None:
        self.assertIsNotNone(runtime_package("linux", "x86_64", "cpu"))

        linux_nvidia = runtime_package("linux", "x86_64", "nvidia")
        self.assertIsNotNone(linux_nvidia)
        assert linux_nvidia is not None
        self.assertFalse(linux_nvidia.source_build)
        self.assertEqual(linux_nvidia.source, "archive-workbench-ai-dist")
        self.assertEqual(len(linux_nvidia.assets), 1)
        self.assertTrue(all(len(asset.sha256) == 64 for asset in linux_nvidia.assets))

        self.assertIsNotNone(runtime_package("darwin", "arm64", "metal"))
        self.assertIsNotNone(runtime_package("darwin", "x86_64", "metal"))

        windows_cuda = runtime_package("windows", "x86_64", "nvidia")
        self.assertIsNotNone(windows_cuda)
        assert windows_cuda is not None
        self.assertEqual(len(windows_cuda.assets), 2)
        self.assertTrue(all(len(asset.sha256) == 64 for asset in windows_cuda.assets))

    def test_runtime_catalog_is_pinned_to_validated_llama_cpp(self) -> None:
        self.assertEqual(PINNED_LLAMA_TAG, "b10903")
        self.assertEqual(PINNED_LLAMA_COMMIT, "481c65f091f74c5e7089dd0a3a1cc6b50cced31e")

    def test_recommended_variant_uses_native_acceleration(self) -> None:
        with mock.patch.object(manager, "_has_nvidia", return_value=True):
            self.assertEqual(manager.recommended_variant("Darwin", "arm64"), "metal")
            self.assertEqual(manager.recommended_variant("Windows", "AMD64"), "nvidia")
            self.assertEqual(manager.recommended_variant("Linux", "x86_64"), "nvidia")
        with mock.patch.object(manager, "_has_nvidia", return_value=False):
            self.assertEqual(manager.recommended_variant("Windows", "AMD64"), "cpu")
            self.assertEqual(manager.recommended_variant("Linux", "x86_64"), "cpu")

    def test_managed_runtime_marker_resolves_executable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            executable = root / "package" / "llama-server"
            executable.parent.mkdir(parents=True)
            executable.write_text("demo", encoding="utf-8")
            marker = {"tag": "b10903", "commit": PINNED_LLAMA_COMMIT, "variant": "cpu", "executable": "package/llama-server"}
            (root / "runtime.json").write_text(json.dumps(marker), encoding="utf-8")
            self.assertEqual(manager.managed_runtime_metadata(root), marker)
            self.assertEqual(manager.managed_runtime_executable(root), executable.resolve())

    def test_install_runtime_reuses_matching_managed_install(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            executable = root / "llama-server"
            executable.write_text("demo", encoding="utf-8")
            marker = {"tag": "b10903", "commit": PINNED_LLAMA_COMMIT, "variant": "cpu", "executable": "llama-server"}
            (root / "runtime.json").write_text(json.dumps(marker), encoding="utf-8")
            with mock.patch.object(manager, "runtime_home", return_value=root), mock.patch.object(manager, "normalize_system", return_value="linux"), mock.patch.object(manager, "normalize_machine", return_value="x86_64"):
                payload = manager.install_runtime(variant="cpu")
            self.assertEqual(payload["status"], "already_installed")
            self.assertEqual(payload["root"], str(root))

    def test_zip_runtime_rejects_parent_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            archive = root / "runtime.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("../escape.txt", "bad")
            with self.assertRaises(InvalidInputError):
                _extract(archive, root / "out")
            self.assertFalse((root / "escape.txt").exists())

    def test_tar_runtime_rejects_parent_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            archive = root / "runtime.tar.gz"
            payload = b"bad"
            with tarfile.open(archive, "w:gz") as bundle:
                info = tarfile.TarInfo("../escape.txt")
                info.size = len(payload)
                bundle.addfile(info, io.BytesIO(payload))
            with self.assertRaises(InvalidInputError):
                _extract(archive, root / "out")
            self.assertFalse((root / "escape.txt").exists())


if __name__ == "__main__":
    unittest.main()
