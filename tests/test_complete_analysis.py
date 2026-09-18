from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _make_exp01(path: Path, *, page_count: int = 5) -> None:
    assets = []
    members: dict[str, bytes] = {}
    for index in range(1, page_count + 1):
        payload = f"FAKE-PAGE-{index}\n".encode()
        member = f"images/pages/doc_{index}_p0001.png"
        asset_id = f"page:doc-{index}:1"
        members[member] = payload
        assets.append(
            {
                "asset_id": asset_id,
                "kind": "page",
                "path": member,
                "sha256": _sha256(payload),
                "byte_size": len(payload),
                "mime_type": "image/png",
                "width": 1200,
                "height": 1600,
                "digital_object_id": f"doc-{index}",
                "page_number": 1,
                "original_filename": f"doc_{index}.tif",
            }
        )

    manifest = {
        "schema_version": "1.0",
        "package_type": "archive_workbench_text_and_images",
        "archive_workbench_version": "test",
        "project_id": "project-test",
        "profile": {},
        "corpus_state_sha256": "0" * 64,
        "options": {
            "include_pages": True,
            "include_regions": False,
            "include_figures": False,
            "include_context": False,
        },
        "text": {
            "path": "text/records.jsonl",
            "record_count": 0,
            "character_count": 0,
            "sha256": _sha256(b""),
        },
        "context": {
            "objects_path": "context/objects.jsonl",
            "objects_sha256": _sha256(b""),
            "object_count": 0,
            "pages_path": "context/pages.jsonl",
            "pages_sha256": _sha256(b""),
            "page_count": 0,
            "documents_path": "context/documents.jsonl",
            "documents_sha256": _sha256(b""),
            "document_count": 0,
        },
        "assets": assets,
        "asset_counts": {"pages": page_count, "regions": 0, "figures": 0},
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        for member, payload in members.items():
            archive.writestr(member, payload)
        archive.writestr("text/records.jsonl", b"")
        archive.writestr("context/objects.jsonl", b"")
        archive.writestr("context/pages.jsonl", b"")
        archive.writestr("context/documents.jsonl", b"")


class CompleteAnalysisTests(unittest.TestCase):
    def test_analyze_consolidates_more_than_three_pages_into_one_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            work = Path(name)
            exp01 = work / "exp01.zip"
            handoff = work / "handoff.zip"
            result = work / "result.zip"
            _make_exp01(exp01, page_count=5)

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "archive_workbench_ai.cli",
                    "analyze",
                    "--input",
                    str(exp01),
                    "--output",
                    str(handoff),
                    "--result-output",
                    str(result),
                    "--profile",
                    "H24",
                    "--backend",
                    "mock",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["target_count"], 5)
            self.assertEqual(payload["internal_request_count"], 2)
            self.assertEqual(payload["internal_max_targets"], 3)
            self.assertEqual(payload["proposal_count"], 5)
            self.assertEqual(payload["handoff_schema_version"], "0.1")

            with zipfile.ZipFile(result) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                self.assertEqual(manifest["target_count"], 5)
                self.assertEqual(manifest["execution_mode"], "complete_exp01")
                self.assertEqual(manifest["batch_count"], 2)
                self.assertEqual(manifest["batch_requests_path"], "requests/batches.jsonl")

                batches = [
                    json.loads(line)
                    for line in archive.read("requests/batches.jsonl").decode("utf-8").splitlines()
                    if line.strip()
                ]
                self.assertEqual([len(batch["targets"]) for batch in batches], [3, 2])
                self.assertTrue(all(len(batch["targets"]) <= 3 for batch in batches))
                batch_target_ids = [
                    target["target_id"]
                    for batch in batches
                    for target in batch["targets"]
                ]
                self.assertEqual(
                    batch_target_ids,
                    [f"page:doc-{index}:1" for index in range(1, 6)],
                )

                items = [
                    json.loads(line)
                    for line in archive.read("results/items.jsonl").decode("utf-8").splitlines()
                    if line.strip()
                ]
                self.assertEqual(len(items), 5)
                self.assertEqual({item["request_id"] for item in items}, {manifest["request_id"]})

            result_sha = _sha256(result.read_bytes())
            with zipfile.ZipFile(handoff) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                proposals = [
                    json.loads(line)
                    for line in archive.read("results/proposals.jsonl").decode("utf-8").splitlines()
                    if line.strip()
                ]
                self.assertEqual(manifest["schema_version"], "0.1")
                self.assertEqual(manifest["proposal_count"], 5)
                self.assertEqual(len(proposals), 5)
                self.assertEqual({row["request_id"] for row in proposals}, {manifest["request_id"]})
                self.assertEqual(
                    {row["provenance"]["result_bundle_sha256"] for row in proposals},
                    {result_sha},
                )


    def test_analyze_without_output_writes_consolidated_handoff_to_downloads(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            work = Path(name)
            exp01 = work / "exp01.zip"
            home = work / "home"
            (home / "Downloads").mkdir(parents=True)
            _make_exp01(exp01, page_count=4)

            env = dict(__import__("os").environ)
            env["HOME"] = str(home)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "archive_workbench_ai.cli",
                    "analyze",
                    "--input",
                    str(exp01),
                    "--profile",
                    "H24",
                    "--backend",
                    "mock",
                ],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            handoff = Path(payload["handoff"])
            self.assertEqual(handoff.parent, home / "Downloads")
            self.assertTrue(handoff.name.startswith("AWAI_HANDOFF_"))
            self.assertTrue(handoff.is_file())
            result = Path(payload["result"])
            self.assertEqual(result.parent, home / "Downloads")
            self.assertTrue(result.name.startswith("AWAI_RESULT_"))
            self.assertTrue(result.is_file())
            self.assertEqual(payload["target_count"], 4)
            self.assertEqual(payload["proposal_count"], 4)
            self.assertEqual(payload["internal_request_count"], 2)


if __name__ == "__main__":
    unittest.main()
