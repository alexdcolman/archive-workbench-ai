from __future__ import annotations

import hashlib
import os
from pathlib import Path
import socket
import time
import urllib.error
import urllib.request

from . import __version__
from .catalog import BOOTSTRAP_MODEL, ModelFile, ModelSpec, model_dir
from .errors import InvalidInputError, RuntimeUnavailableError

_CHUNK_SIZE = 1024 * 1024
_RETRYABLE_HTTP = {408, 425, 429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 6
_DEFAULT_RETRY_DELAYS = (2, 5, 10, 20, 40, 80)
_USER_AGENT = f"archive-workbench-ai/{__version__}"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


def file_status(path: Path, spec: ModelFile) -> dict[str, object]:
    exists = path.is_file()
    actual_size = path.stat().st_size if exists else None
    sha_ok = None
    actual_sha = None
    if exists and (spec.byte_size is None or actual_size == spec.byte_size):
        actual_sha = _sha256(path)
        sha_ok = actual_sha == spec.sha256
    elif exists:
        sha_ok = False
    return {
        "path": str(path),
        "exists": exists,
        "byte_size": actual_size,
        "expected_byte_size": spec.byte_size,
        "sha256": actual_sha,
        "expected_sha256": spec.sha256,
        "verified": bool(exists and sha_ok),
    }


def inspect_model(spec: ModelSpec = BOOTSTRAP_MODEL, verify: bool = False) -> dict[str, object]:
    root = model_dir(spec)
    files = []
    installed = True
    for file_spec in spec.files:
        path = root / file_spec.filename
        if verify:
            status = file_status(path, file_spec)
        else:
            exists = path.is_file() and (file_spec.byte_size is None or path.stat().st_size == file_spec.byte_size)
            status = {
                "path": str(path),
                "exists": path.is_file(),
                "byte_size": path.stat().st_size if path.is_file() else None,
                "expected_byte_size": file_spec.byte_size,
                "expected_sha256": file_spec.sha256,
                "verified": None,
                "size_matches": exists,
            }
        installed = installed and bool(status.get("exists")) and (
            file_spec.byte_size is None or bool(status.get("byte_size") == file_spec.byte_size)
        )
        files.append({"role": file_spec.role, "filename": file_spec.filename, **status})
    return {
        "model_id": spec.model_id,
        "backend": "llama_cpp",
        "installed": installed,
        "real_model": True,
        "status": spec.status,
        "tasks": list(spec.tasks),
        "quantization": spec.quantization,
        "upstream": spec.upstream,
        "note": spec.note,
        "hardware_profiles": list(spec.hardware_profiles),
        "files": files,
    }


def _retry_delay(exc: urllib.error.HTTPError, attempt: int) -> int:
    retry_after = exc.headers.get("Retry-After") if exc.headers else None
    if retry_after:
        try:
            value = int(retry_after)
            return max(1, min(value, 300))
        except ValueError:
            pass
    return _DEFAULT_RETRY_DELAYS[min(attempt, len(_DEFAULT_RETRY_DELAYS) - 1)]


def _hash_existing_partial(path: Path) -> tuple[hashlib._Hash, int]:
    h = hashlib.sha256()
    total = 0
    if path.is_file():
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(_CHUNK_SIZE), b""):
                h.update(chunk)
                total += len(chunk)
    return h, total


def _download_once(spec: ModelFile, partial: Path) -> int:
    existing = partial.stat().st_size if partial.is_file() else 0
    headers = {"User-Agent": _USER_AGENT}
    if existing:
        headers["Range"] = f"bytes={existing}-"
    request = urllib.request.Request(spec.url, headers=headers)

    with urllib.request.urlopen(request, timeout=120) as response:
        status = getattr(response, "status", None) or response.getcode()
        resumed = existing > 0 and status == 206
        if existing > 0 and not resumed:
            # The origin ignored Range; restart safely instead of appending duplicate bytes.
            existing = 0
            partial.unlink(missing_ok=True)

        h, total = _hash_existing_partial(partial)
        mode = "ab" if total else "wb"
        with partial.open(mode) as handle:
            next_report = ((total // (64 * 1024 * 1024)) + 1) * (64 * 1024 * 1024)
            while True:
                chunk = response.read(_CHUNK_SIZE)
                if not chunk:
                    break
                handle.write(chunk)
                h.update(chunk)
                total += len(chunk)
                if total >= next_report:
                    print(
                        f"Descargando {spec.filename}: {total / (1024 * 1024):.1f} MiB",
                        flush=True,
                    )
                    next_report += 64 * 1024 * 1024

    if spec.byte_size is not None and total != spec.byte_size:
        # A short transfer is resumable; only an oversized payload is definitely invalid.
        if total < spec.byte_size:
            raise urllib.error.ContentTooShortError(
                f"Transferencia incompleta para {spec.filename}: {total}/{spec.byte_size} bytes",
                None,
            )
        raise InvalidInputError(
            f"Tamaño descargado incorrecto para {spec.filename}: esperado {spec.byte_size}, obtenido {total}"
        )

    digest = h.hexdigest()
    if digest != spec.sha256:
        raise InvalidInputError(
            f"SHA-256 descargado incorrecto para {spec.filename}: esperado {spec.sha256}, obtenido {digest}"
        )
    return total


def _download_file(spec: ModelFile, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + ".part")

    if partial.is_file() and spec.byte_size is not None and partial.stat().st_size > spec.byte_size:
        partial.unlink()

    last_error: BaseException | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            _download_once(spec, partial)
            partial.replace(dest)
            return
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in _RETRYABLE_HTTP or attempt == _MAX_ATTEMPTS - 1:
                break
            delay = _retry_delay(exc, attempt)
            print(
                f"Descarga temporalmente rechazada para {spec.filename} (HTTP {exc.code}); "
                f"reintento {attempt + 2}/{_MAX_ATTEMPTS} en {delay}s. El archivo parcial se conserva.",
                flush=True,
            )
            time.sleep(delay)
        except (urllib.error.URLError, urllib.error.ContentTooShortError, TimeoutError, socket.timeout, ConnectionError) as exc:
            last_error = exc
            if attempt == _MAX_ATTEMPTS - 1:
                break
            delay = _DEFAULT_RETRY_DELAYS[min(attempt, len(_DEFAULT_RETRY_DELAYS) - 1)]
            print(
                f"Interrupción de descarga para {spec.filename}; "
                f"reintento {attempt + 2}/{_MAX_ATTEMPTS} en {delay}s. El archivo parcial se conserva.",
                flush=True,
            )
            time.sleep(delay)
        except InvalidInputError:
            # Wrong final bytes cannot be repaired by appending; remove the corrupt partial.
            partial.unlink(missing_ok=True)
            raise

    detail = "error de red desconocido"
    if isinstance(last_error, urllib.error.HTTPError):
        detail = f"HTTP {last_error.code}: {last_error.reason}"
    elif last_error is not None:
        detail = str(last_error)
    raise RuntimeUnavailableError(
        f"No se pudo descargar {spec.filename} después de {_MAX_ATTEMPTS} intentos ({detail}). "
        f"La descarga parcial quedó en {partial} y se reanudará en el próximo 'models pull'."
    )


def pull_model(spec: ModelSpec = BOOTSTRAP_MODEL) -> dict[str, object]:
    root = model_dir(spec)
    root.mkdir(parents=True, exist_ok=True)
    for file_spec in spec.files:
        dest = root / file_spec.filename
        current = file_status(dest, file_spec) if dest.exists() else None
        if current and current["verified"]:
            continue
        _download_file(file_spec, dest)
    report = inspect_model(spec, verify=True)
    if not all(bool(item.get("verified")) for item in report["files"]):
        raise RuntimeUnavailableError("El modelo no quedó verificado después de la descarga")
    return report
