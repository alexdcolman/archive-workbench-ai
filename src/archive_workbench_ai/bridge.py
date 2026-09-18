from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .catalog import PROFILE_DEFAULT_MODELS, get_model_spec
from .complete_analysis import analyze_exp01
from .errors import InvalidInputError, RuntimeUnavailableError
from .hashing import sha256_path
from .managed_paths import default_bridge_root

BRIDGE_PROTOCOL = "archive-workbench-ai-bridge/0.1"
BRIDGE_DIRNAME = "archive-workbench-ai-bridge"
MAX_INPUT_BYTES = 8 * 1024 * 1024 * 1024
FAILED_JOB_RETENTION_SECONDS = 7 * 24 * 60 * 60
UNCONSUMED_JOB_RETENTION_SECONDS = 7 * 24 * 60 * 60
STAGING_RETENTION_SECONDS = 24 * 60 * 60


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def bridge_capabilities() -> dict[str, Any]:
    return {
        "bridge_protocol": BRIDGE_PROTOCOL,
        "plugin": "archive-workbench-ai",
        "version": __version__,
        "protocols": ["archive-workbench-ai/0.1"],
        "handoff_schema_ids": ["archive_workbench_ai_result_handoff/0.1"],
        "workflows": {
            "complete_exp01": {
                "command": "analyze",
                "internal_request_max_targets": 3,
                "consolidated_result": True,
                "consolidated_handoff": True,
            }
        },
        "profile_default_models": {
            profile: spec.model_id for profile, spec in PROFILE_DEFAULT_MODELS.items()
        },
    }


def initialize_bridge(root: Path | None = None) -> dict[str, Any]:
    root = (root or default_bridge_root()).expanduser().resolve()
    jobs = root / "jobs"
    jobs.mkdir(parents=True, exist_ok=True)
    secret_path = root / "secret.token"
    if not secret_path.exists():
        secret_path.write_text(secrets.token_hex(32) + "\n", encoding="utf-8")
        try:
            secret_path.chmod(0o600)
        except OSError:
            pass
    secret = secret_path.read_text(encoding="utf-8").strip()
    if len(secret) < 32:
        raise RuntimeUnavailableError("El secreto del puente local es inválido")
    return {
        "status": "ready",
        "root": str(root),
        "protocol": BRIDGE_PROTOCOL,
        "jobs": str(jobs),
        "secret": str(secret_path),
    }


def _load_request(job_dir: Path, secret: str) -> dict[str, Any]:
    request_path = job_dir / "request.json"
    input_path = job_dir / "input.exp01.zip"
    if not request_path.is_file() or not input_path.is_file():
        raise InvalidInputError("El trabajo del puente no contiene request.json e input.exp01.zip")
    if input_path.stat().st_size > MAX_INPUT_BYTES:
        raise InvalidInputError("El EXP-01 excede el límite admitido por el puente local")
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidInputError("request.json del puente no es JSON válido") from exc
    if not isinstance(request, dict):
        raise InvalidInputError("request.json del puente debe ser un objeto JSON")
    allowed = {
        "bridge_protocol", "job_id", "authorization", "created_at", "hardware_profile",
        "model_id", "target_types", "max_output_tokens", "temperature", "seed", "input_sha256"
    }
    extra = set(request) - allowed
    if extra:
        raise InvalidInputError("request.json contiene campos no admitidos: " + ", ".join(sorted(extra)))
    if request.get("bridge_protocol") != BRIDGE_PROTOCOL:
        raise InvalidInputError("Versión de puente no compatible")
    if request.get("job_id") != job_dir.name:
        raise InvalidInputError("La identidad del trabajo no coincide con su directorio")
    supplied = str(request.get("authorization") or "")
    if not hmac.compare_digest(supplied, secret):
        raise InvalidInputError("Autorización del puente local inválida")
    if request.get("hardware_profile") not in {"L12", "H24"}:
        raise InvalidInputError("hardware_profile debe ser L12 o H24")
    target_types = request.get("target_types")
    if target_types != ["page"]:
        raise InvalidInputError("El puente administrado admite únicamente targets page")
    expected_sha = str(request.get("input_sha256") or "")
    if expected_sha != sha256_path(input_path):
        raise InvalidInputError("El SHA-256 del EXP-01 no coincide con request.json")
    return request


def process_job(job_dir: Path, *, backend: str = "llama_cpp") -> dict[str, Any]:
    root = job_dir.parent.parent.resolve()
    secret = (root / "secret.token").read_text(encoding="utf-8").strip()
    request = _load_request(job_dir, secret)
    input_path = job_dir / "input.exp01.zip"
    result_path = job_dir / "result.zip"
    handoff_path = job_dir / "handoff.zip"
    model_id = str(request.get("model_id") or "")
    if model_id:
        try:
            spec = get_model_spec(model_id)
        except KeyError as exc:
            raise InvalidInputError(str(exc)) from exc
    else:
        spec = PROFILE_DEFAULT_MODELS[str(request["hardware_profile"])]
    if str(request["hardware_profile"]) not in spec.hardware_profiles:
        raise InvalidInputError("El modelo solicitado no es compatible con el perfil indicado")
    _atomic_json(job_dir / "status.json", {
        "status": "processing", "job_id": job_dir.name, "updated_at": _utc_now()
    })
    payload = analyze_exp01(
        input_path=input_path,
        handoff_output_path=handoff_path,
        result_output_path=result_path,
        model_spec=spec,
        hardware_profile=str(request["hardware_profile"]),
        backend=backend,
        target_types=("page",),
        seed=int(request.get("seed", 0)),
        max_output_tokens=int(request.get("max_output_tokens", 512)),
        temperature=float(request.get("temperature", 0.0)),
    )
    response = {
        "status": "ok",
        "bridge_protocol": BRIDGE_PROTOCOL,
        "job_id": job_dir.name,
        "completed_at": _utc_now(),
        "analysis_id": payload["analysis_id"],
        "handoff_sha256": payload["handoff_sha256"],
        "result_sha256": payload["result_sha256"],
        "model_id": payload["model_id"],
        "target_count": payload["target_count"],
        "proposal_count": payload["proposal_count"],
        "internal_request_count": payload["internal_request_count"],
        "handoff_schema_version": payload["handoff_schema_version"],
    }
    _atomic_json(job_dir / "response.json", response)
    _atomic_json(job_dir / "status.json", {
        "status": "complete", "job_id": job_dir.name, "updated_at": _utc_now()
    })
    return response


def cleanup_bridge_jobs(root: Path, *, now: float | None = None) -> dict[str, int]:
    """Remove consumed jobs and age out abandoned diagnostics/staging safely."""

    root = root.expanduser().resolve()
    jobs = root / "jobs"
    counts = {"consumed": 0, "failed": 0, "unconsumed": 0, "staging": 0}
    if not jobs.is_dir():
        return counts
    current = time.time() if now is None else float(now)
    for path in tuple(jobs.iterdir()):
        if not path.is_dir():
            continue
        try:
            age = max(0.0, current - path.stat().st_mtime)
        except OSError:
            continue
        if path.name.startswith("."):
            if age >= STAGING_RETENTION_SECONDS:
                shutil.rmtree(path, ignore_errors=True)
                counts["staging"] += 1
            continue
        try:
            uuid.UUID(path.name)
        except ValueError:
            continue
        if (path / "consumed").is_file():
            shutil.rmtree(path, ignore_errors=True)
            counts["consumed"] += 1
            continue
        response_path = path / "response.json"
        if not response_path.is_file():
            continue
        try:
            response = json.loads(response_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            response = {}
        status = response.get("status") if isinstance(response, dict) else None
        if status == "error" and age >= FAILED_JOB_RETENTION_SECONDS:
            shutil.rmtree(path, ignore_errors=True)
            counts["failed"] += 1
        elif status == "ok" and age >= UNCONSUMED_JOB_RETENTION_SECONDS:
            shutil.rmtree(path, ignore_errors=True)
            counts["unconsumed"] += 1
    return counts


def _valid_job_dirs(root: Path) -> list[Path]:
    jobs = root / "jobs"
    if not jobs.is_dir():
        return []
    found: list[Path] = []
    for path in jobs.iterdir():
        if not path.is_dir() or path.name.startswith("."):
            continue
        try:
            uuid.UUID(path.name)
        except ValueError:
            continue
        if not (path / "ready").is_file() or (path / "response.json").exists():
            continue
        found.append(path)
    return sorted(found, key=lambda p: p.name)


def process_pending(root: Path, *, backend: str = "llama_cpp", limit: int | None = None) -> int:
    processed = 0
    for job_dir in _valid_job_dirs(root.resolve()):
        try:
            process_job(job_dir, backend=backend)
        except Exception as exc:
            _atomic_json(job_dir / "response.json", {
                "status": "error",
                "bridge_protocol": BRIDGE_PROTOCOL,
                "job_id": job_dir.name,
                "completed_at": _utc_now(),
                "error": type(exc).__name__,
                "message": str(exc),
            })
            _atomic_json(job_dir / "status.json", {
                "status": "failed", "job_id": job_dir.name, "updated_at": _utc_now()
            })
        processed += 1
        if limit is not None and processed >= limit:
            break
    return processed


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def bridge_status(root: Path | None = None) -> dict[str, Any]:
    root = (root or default_bridge_root()).expanduser().resolve()
    pid_path = root / "bridge.pid"
    pid = None
    if pid_path.is_file():
        try:
            pid = int(pid_path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            pid = None
    return {
        "root": str(root),
        "protocol": BRIDGE_PROTOCOL,
        "initialized": (root / "secret.token").is_file(),
        "running": bool(pid and _pid_alive(pid)),
        "pid": pid,
        "pending_jobs": len(_valid_job_dirs(root)),
        "status_file": str(root / "bridge-status.json"),
        "log_file": str(root / "bridge.log"),
    }


def serve_bridge(root: Path | None = None, *, poll_seconds: float = 0.5, once: bool = False) -> int:
    root = (root or default_bridge_root()).expanduser().resolve()
    initialize_bridge(root)
    lock_path = root / "bridge.lock"
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        current = bridge_status(root)
        if current["running"]:
            raise RuntimeUnavailableError(f"El puente ya está ejecutándose con PID {current['pid']}")
        lock_path.unlink(missing_ok=True)
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    stop = False

    def request_stop(_signum, _frame):
        nonlocal stop
        stop = True

    old_term = signal.signal(signal.SIGTERM, request_stop)
    old_int = signal.signal(signal.SIGINT, request_stop)
    try:
        os.write(fd, f"{os.getpid()}\n".encode("ascii"))
        os.close(fd)
        (root / "bridge.pid").write_text(f"{os.getpid()}\n", encoding="utf-8")
        _atomic_json(root / "capabilities.json", bridge_capabilities())
        _atomic_json(root / "bridge-status.json", {
            "status": "running", "pid": os.getpid(), "started_at": _utc_now(), "protocol": BRIDGE_PROTOCOL
        })
        while not stop:
            cleanup_bridge_jobs(root)
            count = process_pending(root)
            _atomic_json(root / "bridge-status.json", {
                "status": "running", "pid": os.getpid(), "updated_at": _utc_now(),
                "protocol": BRIDGE_PROTOCOL, "processed_last_cycle": count,
            })
            if once:
                break
            time.sleep(max(0.1, poll_seconds))
        return 0
    finally:
        _atomic_json(root / "bridge-status.json", {
            "status": "stopped", "pid": os.getpid(), "updated_at": _utc_now(), "protocol": BRIDGE_PROTOCOL
        })
        (root / "bridge.pid").unlink(missing_ok=True)
        lock_path.unlink(missing_ok=True)
        (root / "capabilities.json").unlink(missing_ok=True)
        signal.signal(signal.SIGTERM, old_term)
        signal.signal(signal.SIGINT, old_int)


def start_bridge(root: Path | None = None, *, wait_seconds: float = 10.0) -> dict[str, Any]:
    root = (root or default_bridge_root()).expanduser().resolve()
    initialize_bridge(root)
    status = bridge_status(root)
    if status["running"]:
        return {**status, "status": "already_running"}
    log_path = root / "bridge.log"
    log = log_path.open("ab")
    kwargs: dict[str, Any] = {
        "stdin": subprocess.DEVNULL,
        "stdout": log,
        "stderr": subprocess.STDOUT,
        "cwd": str(root),
    }
    if os.name == "nt":
        kwargs["creationflags"] = (
            getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
        )
    else:
        kwargs["start_new_session"] = True
    try:
        if getattr(sys, "frozen", False):
            command = [sys.executable, "bridge", "serve", "--root", str(root)]
        else:
            command = [
                sys.executable,
                "-m",
                "archive_workbench_ai.cli",
                "bridge",
                "serve",
                "--root",
                str(root),
            ]
        subprocess.Popen(command, **kwargs)
    finally:
        log.close()
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        status = bridge_status(root)
        if status["running"]:
            return {**status, "status": "started"}
        time.sleep(0.1)
    raise RuntimeUnavailableError(f"El puente no inició. Revisá {log_path}")


def stop_bridge(root: Path | None = None, *, wait_seconds: float = 10.0) -> dict[str, Any]:
    root = (root or default_bridge_root()).expanduser().resolve()
    status = bridge_status(root)
    pid = status.get("pid")
    if not status["running"] or not isinstance(pid, int):
        (root / "capabilities.json").unlink(missing_ok=True)
        return {**status, "status": "not_running"}
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as exc:
        raise RuntimeUnavailableError(f"No se pudo detener el puente con PID {pid}: {exc}") from exc
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return {**bridge_status(root), "status": "stopped"}
        time.sleep(0.1)
    raise RuntimeUnavailableError(f"El puente con PID {pid} no se detuvo dentro del plazo esperado")
