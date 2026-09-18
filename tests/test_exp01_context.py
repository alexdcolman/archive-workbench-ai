from __future__ import annotations

import json
import tempfile
import unittest
import uuid
import zipfile
from pathlib import Path

from archive_workbench_ai.exp01 import SelectedAsset, load_selected_assets
from archive_workbench_ai.llama_cpp_backend import _context_prompt, _schema
from archive_workbench_ai.hashing import sha256_bytes, sha256_path
from archive_workbench_ai.protocol import load_request


class Exp01ContextTests(unittest.TestCase):
    def _make(self, root: Path, *, schema: str) -> tuple[Path, Path]:
        image = b"fake-image"
        objects = b""
        context_meta = {
            "objects_path": "context/objects.jsonl",
            "objects_sha256": sha256_bytes(objects),
            "object_count": 0,
            "pages_path": "context/pages.jsonl",
            "pages_sha256": sha256_bytes(b""),
            "page_count": 0,
            "documents_path": "context/documents.jsonl",
            "documents_sha256": sha256_bytes(b""),
            "document_count": 0,
        }
        if schema == "1.1":
            row = {
                "object_id": "obj-1",
                "digital_object_id": "doc-1",
                "page_number": 1,
                "order_index": 1,
                "object_type": "paragraph",
                "text": "Texto canónico",
                "geometry": [],
                "bbox": {
                    "page": 1,
                    "coordinate_space": "normalized",
                    "x": 0.1,
                    "y": 0.2,
                    "width": 0.3,
                    "height": 0.1,
                },
            }
            objects = (json.dumps(row, ensure_ascii=False) + "\n").encode()
            context_meta["objects_sha256"] = sha256_bytes(objects)
            context_meta["object_count"] = 1
            context_meta["object_geometry"] = {
                "geometry_field": "geometry",
                "bbox_field": "bbox",
                "bbox_format": "x_y_width_height",
                "coordinate_space": "normalized",
            }
        manifest = {
            "schema_version": schema,
            "package_type": "archive_workbench_text_and_images",
            "context": context_meta,
            "assets": [{
                "asset_id": "page:doc-1:1",
                "kind": "page",
                "path": "images/pages/page.png",
                "sha256": sha256_bytes(image),
                "byte_size": len(image),
                "mime_type": "image/png",
                "width": 100,
                "height": 100,
                "digital_object_id": "doc-1",
                "page_number": 1,
            }],
        }
        exp = root / "exp01.zip"
        with zipfile.ZipFile(exp, "w") as z:
            z.writestr("manifest.json", json.dumps(manifest))
            z.writestr("images/pages/page.png", image)
            z.writestr("context/objects.jsonl", objects)
            z.writestr("context/pages.jsonl", b"")
            z.writestr("context/documents.jsonl", b"")
        request = {
            "protocol": "archive-workbench-ai/0.1",
            "request_id": str(uuid.uuid4()),
            "created_at": "2026-09-15T00:00:00Z",
            "task": {"id": "vision_describe", "version": "0.1"},
            "input": {"bundle_type": "exp01", "sha256": sha256_path(exp)},
            "targets": [{"target_id": "page:doc-1:1", "target_type": "page"}],
            "execution": {"network_policy": "offline_required", "hardware_profile": "H24", "seed": 0},
            "generation": {"max_output_tokens": 512, "temperature": 0.0},
            "output": {"schema_id": "vision_describe/0.1"},
        }
        req = root / "request.json"
        req.write_text(json.dumps(request))
        return exp, req

    def test_exp01_11_attaches_spatial_text_context(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            exp, req = self._make(Path(name), schema="1.1")
            request = load_request(req)
            manifest, assets = load_selected_assets(exp, request)
            self.assertEqual(manifest["schema_version"], "1.1")
            self.assertEqual(len(assets[0].context_objects), 1)
            self.assertEqual(assets[0].context_objects[0]["text"], "Texto canónico")
            self.assertEqual(assets[0].context_objects[0]["bbox"]["x"], 0.1)

    def test_exp01_10_remains_supported_without_spatial_context(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            exp, req = self._make(Path(name), schema="1.0")
            request = load_request(req)
            manifest, assets = load_selected_assets(exp, request)
            self.assertEqual(manifest["schema_version"], "1.0")
            self.assertEqual(assets[0].context_objects, ())

    def test_context_prompt_clips_long_canonical_text_per_object(self) -> None:
        asset = SelectedAsset(
            asset_id="page:doc-1:1",
            kind="page",
            path="images/pages/page.png",
            sha256="0" * 64,
            byte_size=1,
            mime_type="image/png",
            width=100,
            height=100,
            metadata={},
            context_objects=(
                {
                    "object_id": "obj-1",
                    "order_index": 1,
                    "object_type": "paragraph",
                    "text": "palabra " * 300,
                    "bbox": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.1},
                },
            ),
        )
        rendered, truncated, clipped_objects, context_chars = _context_prompt(asset)
        self.assertFalse(truncated)
        self.assertEqual(clipped_objects, 1)
        self.assertIn("[…]", rendered)
        self.assertEqual(context_chars, len(rendered))
        self.assertLess(context_chars, 1200)

    def test_generation_schema_bounds_repetitive_lists(self) -> None:
        schema = _schema()
        properties = schema["properties"]
        self.assertEqual(properties["visible_text_notes"]["maxItems"], 4)
        self.assertEqual(properties["document_features"]["maxItems"], 8)
        self.assertEqual(properties["uncertainties"]["maxItems"], 3)



if __name__ == "__main__":
    unittest.main()
