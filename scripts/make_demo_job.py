from __future__ import annotations

import argparse
import hashlib
import json
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("demo_job"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    image = b"P0-DEMO-NOT-A-REAL-IMAGE\n"
    asset_path = "images/pages/demo_p0001.png"
    manifest = {
        "schema_version": "1.0",
        "package_type": "archive_workbench_text_and_images",
        "archive_workbench_version": "demo",
        "project_id": "demo",
        "profile": {},
        "corpus_state_sha256": "0" * 64,
        "options": {"include_pages": True, "include_regions": False, "include_figures": False, "include_context": False},
        "text": {"path": "text/records.jsonl", "record_count": 0, "character_count": 0, "sha256": sha256(b"")},
        "context": {"objects_path": "context/objects.jsonl", "objects_sha256": sha256(b""), "object_count": 0, "pages_path": "context/pages.jsonl", "pages_sha256": sha256(b""), "page_count": 0, "documents_path": "context/documents.jsonl", "documents_sha256": sha256(b""), "document_count": 0},
        "assets": [
            {
                "asset_id": "page:demo:1",
                "kind": "page",
                "path": asset_path,
                "sha256": sha256(image),
                "byte_size": len(image),
                "mime_type": "image/png",
                "width": 1200,
                "height": 1600
            }
        ],
        "asset_counts": {"pages": 1, "regions": 0, "figures": 0}
    }
    exp01 = args.output / "exp01.zip"
    with zipfile.ZipFile(exp01, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        archive.writestr(asset_path, image)
        archive.writestr("text/records.jsonl", b"")
        archive.writestr("context/objects.jsonl", b"")
        archive.writestr("context/pages.jsonl", b"")
        archive.writestr("context/documents.jsonl", b"")

    bundle_hash = hashlib.sha256(exp01.read_bytes()).hexdigest()
    request = {
        "protocol": "archive-workbench-ai/0.1",
        "request_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "task": {"id": "vision_describe", "version": "0.1"},
        "input": {"bundle_type": "exp01", "sha256": bundle_hash},
        "targets": [{"target_id": "page:demo:1", "target_type": "page"}],
        "execution": {"network_policy": "offline_required", "hardware_profile": "auto", "seed": 0},
        "generation": {"max_output_tokens": 256, "temperature": 0.0},
        "output": {"schema_id": "vision_describe/0.1"}
    }
    (args.output / "request.json").write_text(json.dumps(request, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
