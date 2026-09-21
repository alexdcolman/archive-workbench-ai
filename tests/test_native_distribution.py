from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest import mock

from archive_workbench_ai.errors import RuntimeUnavailableError
from archive_workbench_ai.runtime_catalog import RuntimePackage, runtime_package
import archive_workbench_ai.runtime_manager as runtime_manager


ROOT = Path(__file__).parents[1]


class NativeDistributionTests(unittest.TestCase):
    def test_managed_setup_never_source_builds_linux_nvidia_runtime(self) -> None:
        package = RuntimePackage("linux", "x86_64", "nvidia", source_build=True)
        with tempfile.TemporaryDirectory() as tmp:
            with (
                mock.patch.object(runtime_manager, "normalize_system", return_value="linux"),
                mock.patch.object(runtime_manager, "normalize_machine", return_value="x86_64"),
                mock.patch.object(runtime_manager, "recommended_variant", return_value="nvidia"),
                mock.patch.object(runtime_manager, "runtime_package", return_value=package),
                mock.patch.object(runtime_manager, "runtime_home", return_value=Path(tmp) / "runtime"),
            ):
                with self.assertRaises(RuntimeUnavailableError) as ctx:
                    runtime_manager.install_runtime(variant="auto", force=False, allow_source_build=False)
        self.assertIn("no compila toolchains", str(ctx.exception))

    def test_managed_source_build_refusal_happens_before_force_deletion(self) -> None:
        package = RuntimePackage("linux", "x86_64", "nvidia", source_build=True)
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime_root.mkdir()
            marker = runtime_root / "keep.txt"
            marker.write_text("preservar", encoding="utf-8")
            with (
                mock.patch.object(runtime_manager, "normalize_system", return_value="linux"),
                mock.patch.object(runtime_manager, "normalize_machine", return_value="x86_64"),
                mock.patch.object(runtime_manager, "recommended_variant", return_value="nvidia"),
                mock.patch.object(runtime_manager, "runtime_package", return_value=package),
                mock.patch.object(runtime_manager, "runtime_home", return_value=runtime_root),
            ):
                with self.assertRaises(RuntimeUnavailableError):
                    runtime_manager.install_runtime(variant="auto", force=True, allow_source_build=False)
            self.assertEqual(marker.read_text(encoding="utf-8"), "preservar")

    def test_linux_x64_nvidia_catalog_uses_managed_precompiled_runtime(self) -> None:
        package = runtime_package("linux", "x86_64", "nvidia")
        self.assertIsNotNone(package)
        assert package is not None
        self.assertFalse(package.source_build)
        self.assertEqual(package.source, "archive-workbench-ai-dist")
        self.assertEqual(len(package.assets), 1)
        asset = package.assets[0]
        self.assertEqual(asset.filename, "llama-b10903-bin-ubuntu-cuda-12.8-x64.tar.gz")
        self.assertEqual(
            asset.sha256,
            "d41bb204eb09995bfe387950435ddd84635aaaed28fade425d7d35c1bb2cee89",
        )
        self.assertEqual(
            asset.url,
            "https://github.com/alexdcolman/archive-workbench-ai-dist/releases/download/"
            "v0.1.0.dev24/llama-b10903-bin-ubuntu-cuda-12.8-x64.tar.gz",
        )

    def test_downloaded_runtime_marker_uses_package_provenance(self) -> None:
        package = RuntimePackage(
            "linux",
            "x86_64",
            "nvidia",
            source="archive-workbench-ai-dist",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executable = root / "llama-server"
            executable.write_text("binary", encoding="utf-8")
            marker = runtime_manager._write_marker(
                root,
                package=package,
                executable=executable,
                source=package.source,
            )
        self.assertEqual(marker["source"], "archive-workbench-ai-dist")

    def test_native_build_workflow_covers_zero_terminal_platform_candidates(self) -> None:
        source = (ROOT / ".github" / "workflows" / "build-native.yml").read_text(encoding="utf-8")
        for expected in (
            "ubuntu-24.04",
            "windows-2025",
            "macos-15-intel",
            "macos-15",
            "setup --status-json",
            "bridge start --json",
            "bridge stop --json",
            "PyInstaller",
            "shasum -a 256 native-dist/*.dmg",
        ):
            self.assertIn(expected, source)

    def test_linux_package_installs_managed_binary_and_graphical_launcher(self) -> None:
        builder = (ROOT / "packaging" / "linux" / "build_deb.py").read_text(encoding="utf-8")
        desktop = (ROOT / "packaging" / "linux" / "archive-workbench-ai-setup.desktop").read_text(encoding="utf-8")
        self.assertIn('root / "opt" / "archive-workbench-ai"', builder)
        self.assertIn('(usr_bin / "aw-ai").symlink_to("/opt/archive-workbench-ai/aw-ai")', builder)
        self.assertIn("Exec=/opt/archive-workbench-ai/aw-ai setup", desktop)
        self.assertIn("Terminal=false", desktop)

    def test_windows_installer_is_per_user_and_opens_setup_without_terminal(self) -> None:
        iss = (ROOT / "packaging" / "windows" / "ArchiveWorkbenchAI.iss").read_text(encoding="utf-8")
        vbs = (ROOT / "packaging" / "windows" / "setup.vbs").read_text(encoding="utf-8")
        self.assertIn("{localappdata}\\Programs\\Archive Workbench AI", iss)
        self.assertIn("PrivilegesRequired=lowest", iss)
        self.assertIn("wscript.exe", iss)
        self.assertIn('Source: "setup.vbs"', iss)
        self.assertIn("shell.Run cmd, 0, False", vbs)

    def test_macos_bundle_matches_managed_discovery_and_uses_valid_bundle_version(self) -> None:
        builder = (ROOT / "packaging" / "macos" / "build_app.sh").read_text(encoding="utf-8")
        self.assertIn("Archive Workbench AI.app", builder)
        self.assertNotIn("Archive Workbench AI Setup.app", builder)
        self.assertIn("BUNDLE_SHORT_VERSION", builder)
        self.assertIn("<key>CFBundleVersion</key><string>${BUNDLE_BUILD_VERSION}</string>", builder)
        self.assertIn("<key>CFBundleShortVersionString</key><string>${BUNDLE_SHORT_VERSION}</string>", builder)
        self.assertNotIn("<key>CFBundleVersion</key><string>${VERSION}</string>", builder)

    def test_linux_nvidia_runtime_workflow_builds_pinned_commit_off_host(self) -> None:
        source = (ROOT / ".github" / "workflows" / "build-linux-nvidia-runtime.yml").read_text(encoding="utf-8")
        for expected in (
            "481c65f091f74c5e7089dd0a3a1cc6b50cced31e",
            "nvidia/cuda:12.8.1-devel-ubuntu24.04",
            "llama-b10903-bin-ubuntu-cuda-12.8-x64.tar.gz",
            "Free disk space for CUDA candidate build",
            "-DCMAKE_EXE_LINKER_FLAGS=-Wl,--allow-shlib-undefined",
            'cmake --build /build --config Release --target llama-server -j"$(nproc)"',
            "CUDA_LIB_ROOT=/usr/local/cuda/targets/x86_64-linux/lib",
            'LD_LIBRARY_PATH="/tmp/driver-stub:/stage/lib" ldd',
            'compgen -G "/stage/lib/libcuda.so*"',
            "libggml-cuda no conserva dependencia al driver libcuda.so.1",
        ):
            self.assertIn(expected, source)
        self.assertNotIn("--gpus all", source)
        self.assertNotIn("find /usr/local/cuda", source)
        self.assertNotIn("cp -aL", source)


if __name__ == "__main__":
    unittest.main()
