from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import uuid


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=True, capture_output=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke del daemon PyInstaller: el bridge debe sobrevivir al proceso start y conservar sus recursos empaquetados."
    )
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    binary = args.binary.resolve()
    input_path = args.input.resolve()
    root = args.root.resolve()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    start = run(str(binary), "bridge", "start", "--root", str(root), "--json")
    start_payload = json.loads(start.stdout)
    if not start_payload.get("running"):
        raise SystemExit(f"bridge start no quedó running: {start.stdout}")

    try:
        secret = (root / "secret.token").read_text(encoding="utf-8").strip()
        job_id = str(uuid.uuid4())
        job = root / "jobs" / job_id
        job.mkdir(parents=True)
        shutil.copy2(input_path, job / "input.exp01.zip")
        input_sha = hashlib.sha256((job / "input.exp01.zip").read_bytes()).hexdigest()
        request = {
            "bridge_protocol": "archive-workbench-ai-bridge/0.1",
            "job_id": job_id,
            "authorization": secret,
            "created_at": "2026-10-01T00:00:00Z",
            "hardware_profile": "H24",
            "model_id": "ggml-org/gemma-4-26B-A4B-it-GGUF:Q4_0",
            "target_types": ["page"],
            "max_output_tokens": 64,
            "temperature": 0.0,
            "seed": 0,
            "input_sha256": input_sha,
        }
        (job / "request.json").write_text(
            json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (job / "ready").write_text("ready\n", encoding="utf-8")

        deadline = time.monotonic() + args.timeout
        response_path = job / "response.json"
        while time.monotonic() < deadline and not response_path.is_file():
            time.sleep(0.2)
        if not response_path.is_file():
            raise SystemExit("El daemon congelado no procesó el job dentro del timeout")

        response = json.loads(response_path.read_text(encoding="utf-8"))
        serialized = json.dumps(response, ensure_ascii=False)
        forbidden = (
            "_MEI",
            "vision_describe_0_1.txt",
            "No such file or directory",
        )
        hits = [needle for needle in forbidden if needle in serialized]
        if hits:
            raise SystemExit(
                "El daemon perdió recursos PyInstaller después de bridge start: "
                + ", ".join(hits)
                + " :: "
                + serialized
            )

        status = json.loads(run(str(binary), "bridge", "status", "--root", str(root), "--json").stdout)
        if not status.get("running"):
            raise SystemExit(f"El daemon murió después de procesar el job: {status}")

        report = {
            "status": "ok",
            "bridge_start_pid": start_payload.get("pid"),
            "job_id": job_id,
            "job_status": response.get("status"),
            "job_error": response.get("error"),
            "resource_lifetime": "ok",
        }
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0
    finally:
        subprocess.run(
            [str(binary), "bridge", "stop", "--root", str(root), "--json"],
            check=False,
            capture_output=True,
            text=True,
        )


if __name__ == "__main__":
    raise SystemExit(main())
