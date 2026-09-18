from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import archive_workbench_ai.catalog as catalog
from archive_workbench_ai.catalog import MODEL_CATALOG, data_root, get_model_spec


class CatalogTests(unittest.TestCase):
    def test_p2_catalog_has_unique_ids_and_storage_names(self) -> None:
        ids = [spec.model_id for spec in MODEL_CATALOG]
        storage = [spec.storage_name for spec in MODEL_CATALOG]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(storage), len(set(storage)))
        self.assertGreaterEqual(len(ids), 3)

    def test_catalog_resolves_each_model(self) -> None:
        for spec in MODEL_CATALOG:
            self.assertIs(get_model_spec(spec.model_id), spec)
            self.assertEqual({file.role for file in spec.files}, {"model", "mmproj"})

    def test_data_root_prefers_new_name_and_reuses_legacy_install(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            base = Path(temp_name)
            with mock.patch.dict(os.environ, {"XDG_DATA_HOME": str(base)}, clear=False), mock.patch.object(sys, "platform", "linux"):
                os.environ.pop("AW_AI_DATA_HOME", None)
                os.environ.pop("AW_AI01_DATA_HOME", None)
                legacy = base / "archive-workbench-ai01"
                legacy.mkdir()
                self.assertEqual(data_root(), legacy.resolve())
                current = base / "archive-workbench-ai"
                current.mkdir()
                self.assertEqual(data_root(), current.resolve())

    def test_data_root_accepts_legacy_environment_variable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            legacy = Path(temp_name) / "legacy-data"
            with mock.patch.dict(os.environ, {"AW_AI01_DATA_HOME": str(legacy)}, clear=False):
                os.environ.pop("AW_AI_DATA_HOME", None)
                self.assertEqual(data_root(), legacy.resolve())

    def test_data_root_uses_macos_application_support(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            home = Path(temp_name)
            with mock.patch.object(catalog.sys, "platform", "darwin"), mock.patch.object(catalog.Path, "home", classmethod(lambda cls: home)):
                with mock.patch.dict(os.environ, {}, clear=False):
                    os.environ.pop("AW_AI_DATA_HOME", None)
                    os.environ.pop("AW_AI01_DATA_HOME", None)
                    expected = (home / "Library" / "Application Support" / "archive-workbench-ai").resolve()
                    self.assertEqual(catalog.data_root(), expected)


if __name__ == "__main__":
    unittest.main()
