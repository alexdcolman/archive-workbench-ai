from __future__ import annotations

import json
import os
import platform
import tempfile
import time
import uuid
import zipfile
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Any

from . import PROTOCOL_VERSION, __version__
from .catalog import BOOTSTRAP_MODEL, ModelSpec
from .exp01 import SelectedAsset
from .hashing import sha256_path
from .llama_cpp_backend import LlamaCppSession
from .mock_backend import infer as mock_infer
from .protocol import Request
from .runtime import gpu_info


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _artifact(path: Path, root: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256_path(path),
        "byte_size": path.stat().st_size,
    }


def build_result_bundle(
    *,
    request: Request,
    input_path: Path,
    selected_assets: tuple[SelectedAsset, ...],
    output_path: Path,
    backend: str,
    model_spec: ModelSpec = BOOTSTRAP_MODEL,
    result_request_id: str | None = None,
    batch_requests: tuple[dict[str, Any], ...] = (),
) -> dict[str, Any]:
    started_at = _utc_now()
    start = time.perf_counter()
    prompt_text = resources.files("archive_workbench_ai.prompts").joinpath("vision_describe_0_1.txt").read_text(encoding="utf-8")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aw_ai_p1_") as tmp_name:
        root = Path(tmp_name)
        (root / "results").mkdir()
        (root / "prompts").mkdir()
        (root / "metrics").mkdir()
        (root / "raw").mkdir()
        if batch_requests:
            (root / "requests").mkdir()

        item_rows: list[dict[str, Any]] = []
        raw_rows: list[dict[str, Any]] = []
        target_timings: list[dict[str, Any]] = []
        runtime_meta: dict[str, Any]
        model_meta: dict[str, Any]
        effective_extra: dict[str, Any]
        hardware_extra: dict[str, Any]

        session_cm = LlamaCppSession(request, model_spec=model_spec) if backend == "llama_cpp" else None
        if session_cm is not None:
            session = session_cm.__enter__()
        else:
            session = None
        try:
            for asset in selected_assets:
                target_start = time.perf_counter()
                if backend == "llama_cpp":
                    assert session is not None
                    response = session.infer(asset, input_path, prompt_text)
                    output = response.output
                    raw_text = response.raw_text
                    raw_payload: Any = response.raw_response
                    warnings: list[str] = ["experimental_backend"]
                    runtime_meta = response.runtime
                    model_meta = response.model
                    effective_extra = response.effective_configuration
                    hardware_extra = response.hardware
                    performance_extra = response.performance
                else:
                    response = mock_infer(asset, request)
                    output = response.output
                    raw_text = response.raw_text
                    raw_payload = {"raw_text": raw_text}
                    warnings = ["mock_backend"]
                    runtime_meta = {"id": "mock", "revision": "p1-stdlib", "backend": "mock"}
                    model_meta = {
                        "model_id": "mock/vision-describe-p0",
                        "upstream": "internal:p0",
                        "quantization": "none",
                        "sha256": [],
                    }
                    effective_extra = {"backend": "mock"}
                    hardware_extra = {"gpus": gpu_info()}
                    performance_extra = {}

                elapsed_ms = round((time.perf_counter() - target_start) * 1000, 3)
                result_id = str(uuid.uuid4())
                item_rows.append(
                    {
                        "result_id": result_id,
                        "request_id": result_request_id or request.request_id,
                        "task": "vision_describe",
                        "target_id": asset.asset_id,
                        "target_type": asset.kind,
                        "status": "ok",
                        "output_schema_id": "vision_describe/0.1",
                        "output": output,
                        "warnings": warnings,
                    }
                )
                raw_rows.append(
                    {
                        "result_id": result_id,
                        "target_id": asset.asset_id,
                        "backend": backend,
                        "raw_text": raw_text,
                        "raw_response": raw_payload,
                    }
                )
                target_timings.append({"target_id": asset.asset_id, "elapsed_ms": elapsed_ms, "performance": performance_extra})
        finally:
            if session_cm is not None:
                session_cm.__exit__(None, None, None)

        items_path = root / "results" / "items.jsonl"
        raw_path = root / "raw" / "responses.jsonl"
        items_path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in item_rows), encoding="utf-8")
        raw_path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in raw_rows), encoding="utf-8")

        prompt_path = root / "prompts" / "effective_prompt.txt"
        prompt_path.write_text(prompt_text, encoding="utf-8")

        batch_requests_path = None
        if batch_requests:
            batch_requests_path = root / "requests" / "batches.jsonl"
            batch_requests_path.write_text(
                "".join(
                    json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                    for row in batch_requests
                ),
                encoding="utf-8",
            )

        elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
        metrics = {
            "backend": backend,
            "started_at": started_at,
            "finished_at": _utc_now(),
            "elapsed_ms": elapsed_ms,
            "targets": target_timings,
            "network_used": False,
            "model_loaded": backend == "llama_cpp",
            "model_id": model_meta.get("model_id"),
        }
        metrics_path = root / "metrics" / "runtime.json"
        _write_json(metrics_path, metrics)

        artifacts = [_artifact(path, root) for path in sorted(root.rglob("*")) if path.is_file()]
        prompt_artifact = next(item for item in artifacts if item["path"] == "prompts/effective_prompt.txt")
        manifest = {
            "protocol": PROTOCOL_VERSION,
            "request_id": result_request_id or request.request_id,
            "input_sha256": request.input_sha256,
            "status": "complete",
            "plugin": {"id": "archive-workbench-ai", "version": __version__},
            "runtime": runtime_meta,
            "model": model_meta,
            "prompt": {
                "id": "vision_describe_default",
                "version": "0.1",
                "sha256": prompt_artifact["sha256"],
            },
            "requested_configuration": {
                "network_policy": "offline_required",
                "hardware_profile": request.hardware_profile,
                "seed": request.seed,
                "max_output_tokens": request.max_output_tokens,
                "temperature": request.temperature,
            },
            "effective_configuration": {
                "network_policy": "offline_required",
                "hardware_profile": request.hardware_profile,
                "seed": request.seed,
                "max_output_tokens": request.max_output_tokens,
                "temperature": request.temperature,
                **effective_extra,
                "structured_repair_attempts": 0,
            },
            "hardware": {
                "platform": platform.platform(),
                "machine": platform.machine(),
                "python": platform.python_version(),
                "cpu_count": os.cpu_count(),
                **hardware_extra,
            },
            "started_at": started_at,
            "finished_at": metrics["finished_at"],
            "target_count": len(selected_assets),
            "execution_mode": "complete_exp01" if batch_requests else "single_request",
            "batch_count": len(batch_requests) if batch_requests else 1,
            "batch_requests_path": (
                batch_requests_path.relative_to(root).as_posix()
                if batch_requests_path is not None
                else None
            ),
            "artifacts": artifacts,
        }
        manifest_path = root / "manifest.json"
        _write_json(manifest_path, manifest)

        temporary = output_path.with_name(output_path.name + ".tmp")
        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(root.rglob("*")):
                    if path.is_file():
                        archive.write(path, path.relative_to(root).as_posix())
            temporary.replace(output_path)
        finally:
            temporary.unlink(missing_ok=True)

    return manifest
