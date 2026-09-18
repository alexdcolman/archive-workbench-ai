from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

from archive_workbench_ai.benchmark_job import extracted_benchmark_job, prepare_benchmark_job
from archive_workbench_ai.exp01 import load_selected_assets
from archive_workbench_ai.protocol import load_request


class BenchmarkJobTests(unittest.TestCase):
    def _image(self, path: Path, size: tuple[int, int], value: int) -> None:
        Image.new("L", size, color=value).save(path)

    def test_prepare_job_builds_valid_exp01_and_request(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            first = root / "uno.tiff"
            second = root / "dos.png"
            self._image(first, (320, 480), 220)
            self._image(second, (640, 360), 180)
            output = root / "job.zip"

            payload = prepare_benchmark_job(
                image_paths=[first, second],
                hardware_profile="H24",
                output_path=output,
            )
            self.assertEqual(payload["status"], "complete")
            self.assertEqual(payload["targets"], 2)
            self.assertTrue(output.is_file())

            with zipfile.ZipFile(output) as archive:
                self.assertEqual(set(archive.namelist()), {"job_manifest.json", "request.json", "exp01.zip"})
                manifest = json.loads(archive.read("job_manifest.json"))
                self.assertEqual(manifest["hardware_profile"], "H24")
                self.assertEqual([item["source_name"] for item in manifest["sources"]], ["uno.tiff", "dos.png"])
                self.assertNotIn(str(root), json.dumps(manifest))

            with extracted_benchmark_job(output) as (request_path, input_path):
                request = load_request(request_path)
                manifest, assets = load_selected_assets(input_path, request)
                self.assertEqual(request.hardware_profile, "H24")
                self.assertEqual(len(request.targets), 2)
                self.assertEqual(len(assets), 2)
                self.assertEqual(manifest["asset_counts"]["pages"], 2)
                self.assertTrue(all(asset.mime_type == "image/png" for asset in assets))

    def test_prepare_rejects_more_than_three_images(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            images = []
            for index in range(4):
                path = root / f"{index}.png"
                self._image(path, (10, 10), index)
                images.append(path)
            with self.assertRaisesRegex(Exception, "entre 1 y 3"):
                prepare_benchmark_job(image_paths=images, hardware_profile="H24", output_path=root / "job.zip")


if __name__ == "__main__":
    unittest.main()
