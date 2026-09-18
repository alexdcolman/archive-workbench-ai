from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from typing import Any

from . import __version__
from .catalog import ModelSpec
from .errors import PluginError
from .model_store import inspect_model
from .protocol import load_request
from .exp01 import load_selected_assets
from .result_bundle import build_result_bundle
from .runtime import gpu_info


def _downloads_dir() -> Path:
    root = Path.home() / "Downloads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value)[:120]


def _read_zip_json(path: Path, member: str) -> Any:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member).decode("utf-8"))


def run_benchmark(
    *,
    request_path: Path,
    input_path: Path,
    model_specs: list[ModelSpec],
    output_path: Path | None = None,
) -> dict[str, Any]:
    request = load_request(request_path)
    _manifest, assets = load_selected_assets(input_path, request)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_path or (_downloads_dir() / f"AWAI_BENCHMARK_{stamp}.zip")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "plugin": "archive-workbench-ai",
        "version": __version__,
        "phase": "P2",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "request_id": request.request_id,
        "input": str(input_path),
        "gpus": gpu_info(),
        "models": [],
    }

    with tempfile.TemporaryDirectory(prefix="aw_ai_benchmark_") as tmp_name:
        root = Path(tmp_name)
        results_dir = root / "results"
        results_dir.mkdir(parents=True)
        diagnostics_dir = root / "diagnostics"
        diagnostics_dir.mkdir(parents=True)

        for spec in model_specs:
            row: dict[str, Any] = {
                "model_id": spec.model_id,
                "quantization": spec.quantization,
                "status": "pending",
            }
            installed = inspect_model(spec, verify=False)
            if not installed["installed"]:
                row["status"] = "not_installed"
                summary["models"].append(row)
                continue

            result_path = results_dir / f"{_safe_name(spec.storage_name)}.zip"
            started = time.perf_counter()
            try:
                manifest = build_result_bundle(
                    request=request,
                    input_path=input_path,
                    selected_assets=assets,
                    output_path=result_path,
                    backend="llama_cpp",
                    model_spec=spec,
                )
                elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
                metrics = _read_zip_json(result_path, "metrics/runtime.json")
                row.update(
                    {
                        "status": "complete",
                        "elapsed_ms": elapsed_ms,
                        "result_member": f"results/{result_path.name}",
                        "manifest": {
                            "runtime": manifest.get("runtime"),
                            "model": manifest.get("model"),
                            "effective_configuration": manifest.get("effective_configuration"),
                            "hardware": manifest.get("hardware"),
                        },
                        "metrics": metrics,
                    }
                )
            except PluginError as exc:
                message = str(exc)
                row.update(
                    {
                        "status": "failed",
                        "error": exc.code,
                        "message": message,
                        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                    }
                )
                match = re.search(r"Diagnóstico ZIP:\s*(.+?\.zip)(?:\s|$)", message)
                if match:
                    diagnostic_path = Path(match.group(1)).expanduser()
                    if diagnostic_path.is_file():
                        copied = diagnostics_dir / f"{_safe_name(spec.storage_name)}__{diagnostic_path.name}"
                        shutil.copy2(diagnostic_path, copied)
                        row["diagnostic_member"] = f"diagnostics/{copied.name}"
            summary["models"].append(row)

        completed = sum(1 for row in summary["models"] if row["status"] == "complete")
        failed = sum(1 for row in summary["models"] if row["status"] == "failed")
        skipped = sum(1 for row in summary["models"] if row["status"] == "not_installed")
        summary["counts"] = {"complete": completed, "failed": failed, "not_installed": skipped}
        summary["status"] = "complete" if completed and not failed else ("partial" if completed else "failed")

        summary_path = root / "summary.json"
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        temporary = output_path.with_name(output_path.name + ".tmp")
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(summary_path, "summary.json")
            for result_path in sorted(results_dir.glob("*.zip")):
                archive.write(result_path, f"results/{result_path.name}")
            for diagnostic_path in sorted(diagnostics_dir.glob("*.zip")):
                archive.write(diagnostic_path, f"diagnostics/{diagnostic_path.name}")
        temporary.replace(output_path)

    return {"output": str(output_path), **summary}
