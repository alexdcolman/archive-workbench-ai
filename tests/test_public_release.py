from pathlib import Path
import re
import subprocess
import sys
import tomllib
import unittest


ROOT = Path(__file__).parents[1]


class PublicReleaseDocumentationTests(unittest.TestCase):
    def test_package_version_and_public_metadata_are_coherent(self) -> None:
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        init_text = (ROOT / "src" / "archive_workbench_ai" / "__init__.py").read_text(encoding="utf-8")
        version = re.search(r'__version__ = "([^"]+)"', init_text)
        self.assertIsNotNone(version)
        self.assertEqual(pyproject["project"]["version"], version.group(1))
        self.assertEqual(pyproject["project"]["name"], "archive-workbench-ai")
        self.assertTrue((ROOT / "LICENSE").is_file())
        self.assertTrue((ROOT / "NOTICE").is_file())
        self.assertTrue((ROOT / "CITATION.cff").is_file())
        self.assertTrue((ROOT / "THIRD_PARTY_NOTICES.md").is_file())
        self.assertTrue((ROOT / "MANIFEST.in").is_file())
        self.assertTrue((ROOT / "CHANGELOG.md").is_file())

    def test_current_public_docs_do_not_use_internal_phase_guides_as_primary_instructions(self) -> None:
        current = [
            ROOT / "README.md",
            ROOT / "docs" / "INSTALACION.md",
            ROOT / "docs" / "DISTRIBUCION.md",
            ROOT / "docs" / "INTEGRACION_ARCHIVE_WORKBENCH.md",
            ROOT / "docs" / "MODELOS_Y_HARDWARE.md",
            ROOT / "docs" / "PROTOCOLO_0_1.md",
            ROOT / "docs" / "DESARROLLO.md",
            ROOT / "docs" / "RELEASE.md",
        ]
        for path in current:
            self.assertTrue(path.is_file(), path)
        readme = current[0].read_text(encoding="utf-8")
        self.assertNotIn("P0 validó", readme)
        self.assertNotIn("## dev16", readme)
        self.assertNotIn("## dev20", readme)
        self.assertIn("docs/INSTALACION.md", readme)
        self.assertIn("docs/DISTRIBUCION.md", readme)
        self.assertIn("docs/INTEGRACION_ARCHIVE_WORKBENCH.md", readme)

    def test_historical_docs_are_clearly_marked_and_not_current_installation_paths(self) -> None:
        history = ROOT / "docs" / "history"
        names = {
            "INSTALACION_P0.md",
            "INSTALACION_P1.md",
            "INSTALACION_P2.md",
            "BENCHMARK_P1_P2_20260914.md",
            "BENCHMARK_P1_P2_20260915.md",
        }
        self.assertEqual(names, {path.name for path in history.glob("*.md")})
        for path in history.glob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertIn("Documento histórico", text[:800], path)
        for name in ("INSTALACION_P0.md", "INSTALACION_P1.md", "INSTALACION_P2.md"):
            self.assertFalse((ROOT / "docs" / name).exists())

    def test_public_docs_describe_managed_docker_bridge_without_claiming_final_validation(self) -> None:
        integration = (ROOT / "docs" / "INTEGRACION_ARCHIVE_WORKBENCH.md").read_text(encoding="utf-8")
        distribution = (ROOT / "docs" / "DISTRIBUCION.md").read_text(encoding="utf-8")
        self.assertIn("archive-workbench-ai-bridge", integration)
        self.assertIn("buzón", distribution)
        self.assertIn("no abre SQLite", integration)
        self.assertIn("imágenes definitivas", integration)

    def test_runtime_install_command_is_exposed(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "archive_workbench_ai.cli", "runtime", "install", "--help"],
            cwd=ROOT,
            env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--variant", completed.stdout)
        self.assertIn("--force", completed.stdout)


if __name__ == "__main__":
    unittest.main()
