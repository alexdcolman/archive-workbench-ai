from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from archive_workbench_ai.exp01 import SelectedAsset
from archive_workbench_ai.llama_cpp_backend import _effective_prompt


class RunTests(unittest.TestCase):
    def test_demo_job_produces_result_bundle(self) -> None:
        root = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as name:
            job = Path(name) / "job"
            subprocess.run([sys.executable, str(root / "scripts" / "make_demo_job.py"), "--output", str(job)], check=True)
            output = job / "result.zip"
            result = subprocess.run(
                [sys.executable, "-m", "archive_workbench_ai.cli", "run", "--request", str(job / "request.json"), "--input", str(job / "exp01.zip"), "--output", str(output), "--backend", "mock"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
                self.assertIn("manifest.json", names)
                self.assertIn("results/items.jsonl", names)
                manifest = json.loads(archive.read("manifest.json"))
                self.assertEqual(manifest["status"], "complete")
                self.assertEqual(manifest["runtime"]["id"], "mock")

    def test_effective_prompt_uses_canonical_text_as_spatial_context_not_ocr_task(self) -> None:
        asset = SelectedAsset(
            asset_id="page:doc:1",
            kind="page",
            path="images/pages/page.png",
            sha256="0" * 64,
            byte_size=1,
            mime_type="image/png",
            width=1000,
            height=1400,
            metadata={"digital_object_id": "doc", "page_number": 1},
            context_objects=(
                {
                    "object_id": "obj-1",
                    "digital_object_id": "doc",
                    "page_number": 1,
                    "order_index": 1,
                    "object_type": "paragraph",
                    "text": "Texto canónico ya revisado",
                    "bbox": {
                        "page": 1,
                        "coordinate_space": "normalized",
                        "x": 0.1,
                        "y": 0.2,
                        "width": 0.3,
                        "height": 0.1,
                    },
                    "geometry": [],
                },
            ),
        )
        prompt, truncated = _effective_prompt(asset, "PROMPT BASE")
        self.assertFalse(truncated)
        self.assertIn("Texto canónico ya revisado", prompt)
        self.assertIn("x=0.1,y=0.2,width=0.3,height=0.1", prompt)
        self.assertIn("no es OCR a rehacer", prompt)


if __name__ == "__main__":
    unittest.main()
