from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import mimetypes
from pathlib import Path
import socket
import subprocess
import tempfile
import os
from datetime import datetime, timezone
import time
import urllib.error
import urllib.request
import zipfile
from typing import Any
import threading

_MIN_STRUCTURED_OUTPUT_TOKENS = 768

from .catalog import BOOTSTRAP_MODEL, ModelSpec, mmproj_path, model_path
from .errors import InferenceError, PluginError, RuntimeUnavailableError
from .exp01 import SelectedAsset
from .protocol import Request
from .runtime import RuntimeCommand, detect_runtime, gpu_info


@dataclass(slots=True, frozen=True)
class LlamaResponse:
    output: dict[str, Any]
    raw_text: str
    raw_response: dict[str, Any]
    runtime: dict[str, Any]
    model: dict[str, Any]
    effective_configuration: dict[str, Any]
    hardware: dict[str, Any]
    performance: dict[str, Any]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _get_json(url: str, timeout: float = 3.0) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_ready(base: str, proc: subprocess.Popen[str], log_path: Path, timeout: float = 120.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-6000:] if log_path.exists() else ""
            raise RuntimeUnavailableError(f"llama-server terminó durante el arranque (rc={proc.returncode}).\n{tail}")
        try:
            return _get_json(base + "/v1/models", timeout=2.0)
        except Exception as exc:  # local readiness probe only
            last_error = str(exc)
            time.sleep(0.5)
    tail = log_path.read_text(encoding="utf-8", errors="replace")[-6000:] if log_path.exists() else ""
    raise RuntimeUnavailableError(f"llama-server no quedó listo dentro del timeout: {last_error}\n{tail}")


def _server_args(runtime: RuntimeCommand, request: Request, port: int, model_spec: ModelSpec) -> tuple[list[str], dict[str, Any]]:
    m = model_path(model_spec)
    mm = mmproj_path(model_spec)
    if not m.is_file() or not mm.is_file():
        raise RuntimeUnavailableError(f"Falta el modelo {model_spec.model_id}. Ejecutá `aw-ai models pull {model_spec.model_id}`.")

    profile = request.hardware_profile
    fit_target = 1536 if profile in {"auto", "L12"} else 3072
    ctx_size = 8192 if profile in {"auto", "L12"} else 16384
    # Gemma 4 vision uses non-causal attention over the complete image-token block.
    # llama.cpp requires n_ubatch >= n_tokens for that decode path; the default
    # physical micro-batch (512) can abort on ordinary document images.
    gemma4_multimodal = "gemma-4-" in model_spec.model_id.lower()
    batch_size = 2048 if gemma4_multimodal else None
    ubatch_size = 2048 if gemma4_multimodal else None
    args = [
        *runtime.argv_prefix,
        "-m", str(m),
        "--mmproj", str(mm),
        "--host", "127.0.0.1",
        "--port", str(port),
        "--parallel", "1",
        "--ctx-size", str(ctx_size),
    ]
    if batch_size is not None and ubatch_size is not None:
        args.extend([
            "--batch-size", str(batch_size),
            "--ubatch-size", str(ubatch_size),
        ])
    args.extend([
        # Deliberately do not set --n-gpu-layers. llama.cpp --fit can only
        # reduce GPU residency when n_gpu_layers was not pinned by the user.
        "--fit", "on",
        "--fit-target", str(fit_target),
        "--fit-ctx", "4096",
        "--flash-attn", "on",
        "--cache-type-k", "q8_0",
        "--cache-type-v", "q8_0",
    ])
    effective = {
        "backend": "llama_cpp",
        "hardware_profile": profile,
        "ctx_size_requested": ctx_size,
        "batch_size": batch_size,
        "ubatch_size": ubatch_size,
        "gemma4_multimodal_batch_policy": "2048/2048" if gemma4_multimodal else "runtime_default",
        "fit": "on",
        "fit_target_mib": fit_target,
        "fit_ctx_min": 4096,
        "n_gpu_layers_policy": "auto_unpinned",
        "flash_attention": "on",
        "cache_type_k": "q8_0",
        "cache_type_v": "q8_0",
        "mmproj_offload": True,
    }
    return args, effective


_MAX_CONTEXT_CHARS = 7000
_MAX_CONTEXT_OBJECT_TEXT_CHARS = 420

_COMPACT_RETRY_INSTRUCTION = """

REINTENTO COMPACTO OBLIGATORIO:
La respuesta anterior excedió el presupuesto. Respondé de nuevo desde cero y mucho más breve.
- description: 2 a 4 oraciones; describí organización visual/material, no el contenido temático.
- visible_text_notes: máximo 4 ítems; cada ítem breve; no copies párrafos ni listas del contexto canónico.
- document_features: máximo 8 rasgos, sin duplicados.
- uncertainties: máximo 3 dudas visuales concretas.
No reproduzcas bloques textuales completos aunque estén disponibles en el contexto.
"""


def _context_prompt(asset: SelectedAsset) -> tuple[str, bool]:
    if not asset.context_objects:
        return "", False
    lines = [
        "\n\nCONTEXTO CANÓNICO DE ARCHIVE WORKBENCH (no es OCR a rehacer):",
        "Las coordenadas bbox son normalizadas respecto de la página, con origen arriba-izquierda y formato x,y,width,height.",
        "Usá este texto y su posición para interpretar relaciones visuales. No premies ni intentes una retranscripción exhaustiva del texto ya provisto.",
    ]
    used = sum(len(line) + 1 for line in lines)
    truncated = False
    clipped_objects = 0
    for obj in asset.context_objects:
        bbox = obj.get("bbox")
        bbox_text = "sin_bbox"
        if isinstance(bbox, dict):
            bbox_text = ",".join(
                f"{key}={bbox.get(key)}" for key in ("x", "y", "width", "height")
            )
        header = (
            f"[objeto={obj.get('object_id')} orden={obj.get('order_index')} "
            f"tipo={obj.get('object_type')} {bbox_text}] "
        )
        text = " ".join(str(obj.get("text") or "").replace("\x00", "").split())
        if len(text) > _MAX_CONTEXT_OBJECT_TEXT_CHARS:
            clipped_text = text[: _MAX_CONTEXT_OBJECT_TEXT_CHARS - 4].rsplit(" ", 1)[0]
            text = clipped_text + " […]"
            clipped_objects += 1
        entry = header + text
        remaining = _MAX_CONTEXT_CHARS - used
        if remaining <= 0:
            truncated = True
            break
        if len(entry) + 1 > remaining:
            entry = entry[: max(0, remaining - 1)]
            truncated = True
        lines.append(entry)
        used += len(entry) + 1
        if truncated:
            break
    if truncated:
        lines.append("[contexto truncado por límite determinista del plugin]")
    rendered = "\n".join(lines)
    return rendered, truncated, clipped_objects, len(rendered)


def _effective_prompt(asset: SelectedAsset, prompt_text: str) -> tuple[str, bool]:
    context, truncated, _clipped_objects, _context_chars = _context_prompt(asset)
    return prompt_text.rstrip() + context + "\n", truncated


def _effective_prompt_with_stats(
    asset: SelectedAsset, prompt_text: str
) -> tuple[str, bool, int, int]:
    context, truncated, clipped_objects, context_chars = _context_prompt(asset)
    return prompt_text.rstrip() + context + "\n", truncated, clipped_objects, context_chars


def _read_asset(input_path: Path, asset: SelectedAsset) -> bytes:
    with zipfile.ZipFile(input_path) as archive:
        return archive.read(asset.path)


def _schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["description", "visible_text_notes", "document_features", "uncertainties"],
        "properties": {
            "description": {"type": "string"},
            "visible_text_notes": {"type": "array", "maxItems": 4, "items": {"type": "string"}},
            "document_features": {"type": "array", "maxItems": 8, "items": {"type": "string"}},
            "uncertainties": {"type": "array", "maxItems": 3, "items": {"type": "string"}},
        },
    }


def _downloads_dir() -> Path:
    explicit = os.environ.get("AW_AI_DIAGNOSTICS_DOWNLOADS_DIR") or os.environ.get("AW_AI01_DIAGNOSTICS_DOWNLOADS_DIR")
    root = Path(explicit).expanduser() if explicit else Path.home() / "Downloads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _persist_diagnostics(
    *,
    request: Request,
    asset: SelectedAsset,
    raw_response: Any | None,
    raw_text: str | None,
    log_path: Path | None,
    server_models: dict[str, Any] | None,
    reason: str,
) -> Path:
    """Write one user-shareable diagnostics ZIP directly to Downloads.

    No persistent diagnostics directory is created elsewhere. Temporary llama-server
    logs remain inside the session tempdir and are copied into the ZIP on failure.
    """
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_request = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in request.request_id)[:80]
    safe_asset = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in asset.asset_id)[:80]
    zip_path = _downloads_dir() / f"AWAI_DIAGNOSTICO_{stamp}_{safe_request}_{safe_asset}.zip"

    summary = {
        "request_id": request.request_id,
        "target_id": asset.asset_id,
        "target_type": asset.kind,
        "hardware_profile": request.hardware_profile,
        "temperature": request.temperature,
        "seed": request.seed,
        "max_output_tokens": request.max_output_tokens,
    }
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("reason.txt", reason + "\n")
        archive.writestr("raw_text.txt", raw_text or "")
        archive.writestr(
            "raw_response.json",
            json.dumps(raw_response, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        archive.writestr(
            "server_models.json",
            json.dumps(server_models, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        archive.writestr(
            "request_summary.json",
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        if log_path is not None and log_path.is_file():
            archive.writestr("llama-server.log", log_path.read_text(encoding="utf-8", errors="replace"))
    return zip_path



def _persist_startup_diagnostics(
    *,
    request: Request,
    model_spec: ModelSpec,
    runtime: RuntimeCommand,
    effective_configuration: dict[str, Any],
    log_path: Path | None,
    reason: str,
) -> Path:
    """Persist llama-server startup/load failures directly to Downloads."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_request = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in request.request_id)[:80]
    safe_model = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in model_spec.storage_name)[:100]
    zip_path = _downloads_dir() / f"AWAI_DIAGNOSTICO_{stamp}_{safe_request}_{safe_model}_startup.zip"
    payload = {
        "request_id": request.request_id,
        "hardware_profile": request.hardware_profile,
        "model_id": model_spec.model_id,
        "quantization": model_spec.quantization,
        "runtime": {
            "executable": runtime.executable,
            "revision": runtime.revision,
            "build_number": runtime.build_number,
            "version_text": runtime.version_text,
            "validation_status": runtime.status,
        },
        "effective_configuration": effective_configuration,
        "gpus": gpu_info(),
    }
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("reason.txt", reason + "\n")
        archive.writestr(
            "startup_context.json",
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        if log_path is not None and log_path.is_file():
            archive.writestr("llama-server.log", log_path.read_text(encoding="utf-8", errors="replace"))
    return zip_path


def _validate_output(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InferenceError("La salida estructurada del modelo no es un objeto JSON")
    expected = {"description", "visible_text_notes", "document_features", "uncertainties"}
    if set(value) != expected:
        raise InferenceError("La salida estructurada del modelo no cumple vision_describe/0.1")
    if not isinstance(value["description"], str):
        raise InferenceError("description no es texto")
    for key in ("visible_text_notes", "document_features", "uncertainties"):
        if not isinstance(value[key], list) or not all(isinstance(item, str) for item in value[key]):
            raise InferenceError(f"{key} no es una lista de textos")
    return value


class _ResourceSampler:
    """Best-effort peak sampler for one local llama-server process.

    Uses only stdlib plus nvidia-smi when available. Sampling failures never abort
    inference; missing measurements are reported as null/absent.
    """

    def __init__(self, pid: int, interval_s: float = 0.25):
        self.pid = pid
        self.interval_s = interval_s
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.rss_peak_mib: float | None = None
        self.gpu_process_peak_mib: float | None = None
        self.samples = 0

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="aw-ai-resource-sampler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _sample_rss(self) -> float | None:
        status = Path(f"/proc/{self.pid}/status")
        try:
            for line in status.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        return float(parts[1]) / 1024.0
        except OSError:
            return None
        return None

    def _sample_gpu(self) -> float | None:
        try:
            completed = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-compute-apps=pid,used_memory",
                    "--format=csv,noheader,nounits",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=2.0,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if completed.returncode != 0:
            return None
        total = 0.0
        found = False
        for line in completed.stdout.splitlines():
            parts = [part.strip() for part in line.split(",")]
            if len(parts) < 2:
                continue
            try:
                pid = int(parts[0])
                used = float(parts[1])
            except ValueError:
                continue
            if pid == self.pid:
                total += used
                found = True
        return total if found else None

    def _loop(self) -> None:
        while not self._stop.is_set():
            rss = self._sample_rss()
            gpu = self._sample_gpu()
            if rss is not None:
                self.rss_peak_mib = rss if self.rss_peak_mib is None else max(self.rss_peak_mib, rss)
            if gpu is not None:
                self.gpu_process_peak_mib = gpu if self.gpu_process_peak_mib is None else max(self.gpu_process_peak_mib, gpu)
            self.samples += 1
            self._stop.wait(self.interval_s)

    def snapshot(self) -> dict[str, Any]:
        return {
            "rss_peak_mib": round(self.rss_peak_mib, 3) if self.rss_peak_mib is not None else None,
            "gpu_process_peak_mib": round(self.gpu_process_peak_mib, 3) if self.gpu_process_peak_mib is not None else None,
            "samples": self.samples,
            "sample_interval_ms": round(self.interval_s * 1000, 3),
        }


class LlamaCppSession:
    def __init__(self, request: Request, model_spec: ModelSpec = BOOTSTRAP_MODEL):
        runtime = detect_runtime()
        if runtime is None:
            raise RuntimeUnavailableError(
                "No se encontró llama-server/llama. Instalá o compilá llama.cpp y dejá llama-server en PATH, o definí AW_AI_LLAMA_SERVER."
            )
        if runtime.status == "too_old":
            raise RuntimeUnavailableError(
                f"llama.cpp demasiado antiguo para P1: build={runtime.build_number}; mínimo probado={10903}."
            )
        self.runtime = runtime
        self.request = request
        self.model_spec = model_spec
        self.port = _free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.tempdir: tempfile.TemporaryDirectory[str] | None = None
        self.proc: subprocess.Popen[str] | None = None
        self.log_path: Path | None = None
        self.server_models: dict[str, Any] | None = None
        self.effective: dict[str, Any] = {}
        self.load_elapsed_ms: float | None = None
        self.sampler: _ResourceSampler | None = None

    def __enter__(self) -> "LlamaCppSession":
        self.tempdir = tempfile.TemporaryDirectory(prefix="aw_ai_llama_")
        root = Path(self.tempdir.name)
        self.log_path = root / "llama-server.log"
        args, effective = _server_args(self.runtime, self.request, self.port, self.model_spec)
        self.effective = effective
        load_started = time.perf_counter()
        log = self.log_path.open("w", encoding="utf-8")
        try:
            self.proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, text=True)
            self.sampler = _ResourceSampler(self.proc.pid)
            self.sampler.start()
        finally:
            log.close()
        try:
            self.server_models = _wait_ready(self.base, self.proc, self.log_path)
        except PluginError as exc:
            diagnostics = _persist_startup_diagnostics(
                request=self.request,
                model_spec=self.model_spec,
                runtime=self.runtime,
                effective_configuration=self.effective,
                log_path=self.log_path,
                reason=str(exc),
            )
            # __exit__ is not called when __enter__ fails, so clean up here.
            if self.sampler is not None:
                self.sampler.stop()
            if self.proc is not None and self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait(timeout=5)
            if self.tempdir is not None:
                self.tempdir.cleanup()
                self.tempdir = None
            raise RuntimeUnavailableError(f"{exc}. Diagnóstico ZIP: {diagnostics}") from exc
        except Exception as exc:
            reason = f"Fallo inesperado durante el arranque de llama-server: {exc}"
            diagnostics = _persist_startup_diagnostics(
                request=self.request,
                model_spec=self.model_spec,
                runtime=self.runtime,
                effective_configuration=self.effective,
                log_path=self.log_path,
                reason=reason,
            )
            if self.sampler is not None:
                self.sampler.stop()
            if self.proc is not None and self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait(timeout=5)
            if self.tempdir is not None:
                self.tempdir.cleanup()
                self.tempdir = None
            raise RuntimeUnavailableError(f"{reason}. Diagnóstico ZIP: {diagnostics}") from exc
        self.load_elapsed_ms = round((time.perf_counter() - load_started) * 1000, 3)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.sampler is not None:
            self.sampler.stop()
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        if self.tempdir is not None:
            self.tempdir.cleanup()

    def infer(self, asset: SelectedAsset, input_path: Path, prompt_text: str) -> LlamaResponse:
        effective_prompt, context_truncated, context_clipped_objects, context_chars = (
            _effective_prompt_with_stats(asset, prompt_text)
        )
        payload = _read_asset(input_path, asset)
        mime = asset.mime_type or mimetypes.guess_type(asset.path)[0] or "image/png"
        data_url = f"data:{mime};base64," + base64.b64encode(payload).decode("ascii")
        model_id = "model"
        try:
            data = (self.server_models or {}).get("data")
            if isinstance(data, list) and data and isinstance(data[0], dict) and isinstance(data[0].get("id"), str):
                model_id = data[0]["id"]
        except Exception:
            pass
        body = {
            "model": model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": effective_prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            "temperature": self.request.temperature,
            "seed": self.request.seed,
            "max_tokens": self.request.max_output_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "vision_describe_0_1",
                    "strict": True,
                    "schema": _schema(),
                },
            },
            "chat_template_kwargs": {"enable_thinking": False},
            "reasoning_effort": "none",
        }
        self.effective["exp01_context_objects"] = len(asset.context_objects)
        self.effective["exp01_context_truncated"] = context_truncated
        self.effective["exp01_context_text_clipped_objects"] = context_clipped_objects
        self.effective["exp01_context_prompt_chars"] = context_chars

        def request_completion(max_tokens: int, *, compact_retry: bool = False) -> dict[str, Any]:
            attempt_body = dict(body)
            attempt_body["max_tokens"] = max_tokens
            if compact_retry:
                attempt_body["messages"] = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": effective_prompt + _COMPACT_RETRY_INSTRUCTION,
                            },
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ]
            http_request = urllib.request.Request(
                self.base + "/v1/chat/completions",
                data=json.dumps(attempt_body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(http_request, timeout=300) as response:
                    response_text = response.read().decode("utf-8", errors="replace")
                try:
                    return json.loads(response_text)
                except json.JSONDecodeError as exc:
                    reason = f"llama-server devolvió una respuesta HTTP no JSON: {exc}"
                    diagnostics = _persist_diagnostics(
                        request=self.request,
                        asset=asset,
                        raw_response=None,
                        raw_text=response_text,
                        log_path=self.log_path,
                        server_models=self.server_models,
                        reason=reason,
                    )
                    raise InferenceError(f"{reason}. Diagnóstico ZIP: {diagnostics}") from exc
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                reason = f"llama-server respondió HTTP {exc.code}: {detail[-4000:]}"
                diagnostics = _persist_diagnostics(
                    request=self.request,
                    asset=asset,
                    raw_response=None,
                    raw_text=detail,
                    log_path=self.log_path,
                    server_models=self.server_models,
                    reason=reason,
                )
                raise InferenceError(f"{reason}. Diagnóstico ZIP: {diagnostics}") from exc
            except OSError as exc:
                rc = self.proc.poll() if self.proc is not None else None
                reason = f"Fallo al consultar llama-server: {exc}"
                if rc is not None:
                    reason += f"; llama-server terminó con rc={rc}"
                diagnostics = _persist_diagnostics(
                    request=self.request,
                    asset=asset,
                    raw_response=None,
                    raw_text=None,
                    log_path=self.log_path,
                    server_models=self.server_models,
                    reason=reason,
                )
                raise InferenceError(f"{reason}. Diagnóstico ZIP: {diagnostics}") from exc

        generation_attempts: list[dict[str, Any]] = []
        effective_max_tokens = self.request.max_output_tokens
        raw = request_completion(effective_max_tokens)
        finish_reason = None
        try:
            finish_reason = raw["choices"][0].get("finish_reason")
        except (KeyError, IndexError, TypeError, AttributeError):
            pass
        generation_attempts.append(
            {
                "max_output_tokens": effective_max_tokens,
                "finish_reason": finish_reason,
                "mode": "normal",
            }
        )

        if finish_reason == "length":
            retry_max_tokens = max(_MIN_STRUCTURED_OUTPUT_TOKENS, effective_max_tokens * 2)
            if retry_max_tokens > effective_max_tokens:
                effective_max_tokens = retry_max_tokens
                raw = request_completion(effective_max_tokens, compact_retry=True)
                retry_finish_reason = None
                try:
                    retry_finish_reason = raw["choices"][0].get("finish_reason")
                except (KeyError, IndexError, TypeError, AttributeError):
                    pass
                generation_attempts.append({
                    "max_output_tokens": effective_max_tokens,
                    "finish_reason": retry_finish_reason,
                    "mode": "compact_retry",
                })

        try:
            message = raw["choices"][0]["message"]
            raw_text = message["content"]
        except (KeyError, IndexError, TypeError) as exc:
            diagnostics = _persist_diagnostics(
                request=self.request,
                asset=asset,
                raw_response=raw,
                raw_text=None,
                log_path=self.log_path,
                server_models=self.server_models,
                reason="Respuesta OpenAI-compatible sin choices[0].message.content",
            )
            raise InferenceError(
                f"Respuesta OpenAI-compatible sin choices[0].message.content. Diagnóstico ZIP: {diagnostics}"
            ) from exc
        if not isinstance(raw_text, str):
            diagnostics = _persist_diagnostics(
                request=self.request,
                asset=asset,
                raw_response=raw,
                raw_text=repr(raw_text),
                log_path=self.log_path,
                server_models=self.server_models,
                reason="message.content no es texto",
            )
            raise InferenceError(f"message.content no es texto. Diagnóstico ZIP: {diagnostics}")
        try:
            structured = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            reasoning = message.get("reasoning_content") if isinstance(message, dict) else None
            final_finish_reason = generation_attempts[-1].get("finish_reason") if generation_attempts else None
            reason = "El modelo no devolvió JSON válido"
            if final_finish_reason == "length":
                reason = f"La salida estructurada quedó truncada tras {effective_max_tokens} tokens"
            if raw_text == "":
                reason += "; message.content está vacío"
            if isinstance(reasoning, str) and reasoning:
                reason += f"; reasoning_content contiene {len(reasoning)} caracteres"
            diagnostics = _persist_diagnostics(
                request=self.request,
                asset=asset,
                raw_response=raw,
                raw_text=raw_text,
                log_path=self.log_path,
                server_models=self.server_models,
                reason=reason,
            )
            raise InferenceError(
                f"{reason}. Diagnóstico ZIP: {diagnostics}"
            ) from exc
        try:
            structured = _validate_output(structured)
        except InferenceError as exc:
            diagnostics = _persist_diagnostics(
                request=self.request,
                asset=asset,
                raw_response=raw,
                raw_text=raw_text,
                log_path=self.log_path,
                server_models=self.server_models,
                reason=str(exc),
            )
            raise InferenceError(f"{exc}. Diagnóstico ZIP: {diagnostics}") from exc

        return LlamaResponse(
            output=structured,
            raw_text=raw_text,
            raw_response=raw,
            runtime={
                "id": "llama.cpp",
                "revision": self.runtime.revision,
                "build_number": self.runtime.build_number,
                "version_text": self.runtime.version_text,
                "backend": "llama_cpp",
                "validation_status": self.runtime.status,
            },
            model={
                "model_id": self.model_spec.model_id,
                "upstream": self.model_spec.upstream,
                "quantization": self.model_spec.quantization,
                "sha256": [file.sha256 for file in self.model_spec.files],
                "status": self.model_spec.status,
            },
            effective_configuration={
                **self.effective,
                "max_output_tokens_requested": self.request.max_output_tokens,
                "max_output_tokens_effective": effective_max_tokens,
                "output_budget_auto_expanded": effective_max_tokens != self.request.max_output_tokens,
                "generation_attempts": generation_attempts,
            },
            hardware={"gpus": gpu_info()},
            performance={
                "server_load_elapsed_ms": self.load_elapsed_ms,
                "resource_peaks": self.sampler.snapshot() if self.sampler is not None else {},
                "timings": raw.get("timings") if isinstance(raw, dict) else None,
                "usage": raw.get("usage") if isinstance(raw, dict) else None,
            },
        )
