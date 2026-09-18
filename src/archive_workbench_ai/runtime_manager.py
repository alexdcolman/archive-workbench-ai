from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

from .catalog import data_root
from .errors import InvalidInputError, RuntimeUnavailableError
from .runtime_catalog import (
    PINNED_LLAMA_BUILD,
    PINNED_LLAMA_COMMIT,
    PINNED_LLAMA_TAG,
    RuntimeAsset,
    RuntimePackage,
    runtime_package,
)

_MARKER = "runtime.json"
_CHUNK = 1024 * 1024
_RETRIES = (2, 5, 10, 20)


def normalize_system(value: str | None = None) -> str:
    raw = (value or platform.system()).casefold()
    if raw.startswith("linux"):
        return "linux"
    if raw.startswith("darwin") or raw.startswith("mac"):
        return "darwin"
    if raw.startswith("windows") or raw.startswith("win"):
        return "windows"
    return raw


def normalize_machine(value: str | None = None, *, system: str | None = None) -> str:
    raw = (value or platform.machine()).casefold().replace("-", "_")
    normalized_system = normalize_system(system)
    if raw in {"amd64", "x64", "x86_64"}:
        return "x86_64"
    if raw in {"arm64", "aarch64"}:
        return "arm64" if normalized_system in {"darwin", "windows"} else "aarch64"
    return raw


def runtime_home() -> Path:
    explicit = os.environ.get("AW_AI_RUNTIME_HOME") or os.environ.get("AW_AI01_RUNTIME_HOME")
    if explicit:
        return Path(explicit).expanduser().resolve()
    return data_root() / "runtime" / f"llama.cpp-{PINNED_LLAMA_TAG}"


def _has_nvidia() -> bool:
    return shutil.which("nvidia-smi") is not None


def recommended_variant(system: str | None = None, machine: str | None = None) -> str:
    system = normalize_system(system)
    machine = normalize_machine(machine, system=system)
    if system == "darwin":
        return "metal"
    if system in {"linux", "windows"} and _has_nvidia() and machine in {"x86_64", "aarch64", "arm64"}:
        return "nvidia"
    return "cpu"


def managed_runtime_metadata(root: Path | None = None) -> dict[str, object] | None:
    marker = (root or runtime_home()) / _MARKER
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def managed_runtime_executable(root: Path | None = None) -> Path | None:
    base = root or runtime_home()
    payload = managed_runtime_metadata(base)
    relative = payload.get("executable") if payload else None
    if isinstance(relative, str) and relative:
        candidate = (base / relative).resolve()
        if candidate.is_file():
            return candidate
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(asset: RuntimeAsset, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    last_error: BaseException | None = None
    for attempt in range(len(_RETRIES) + 1):
        try:
            request = urllib.request.Request(
                asset.url,
                headers={"User-Agent": "archive-workbench-ai-runtime-installer"},
            )
            with urllib.request.urlopen(request, timeout=180) as response, partial.open("wb") as output:
                while True:
                    chunk = response.read(_CHUNK)
                    if not chunk:
                        break
                    output.write(chunk)
            actual = _sha256(partial)
            if actual != asset.sha256:
                partial.unlink(missing_ok=True)
                raise InvalidInputError(
                    f"El runtime descargado no coincide con el SHA-256 publicado para {asset.filename}."
                )
            partial.replace(destination)
            return
        except InvalidInputError:
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt >= len(_RETRIES):
                break
            time.sleep(_RETRIES[attempt])
    raise RuntimeUnavailableError(
        f"No se pudo descargar {asset.filename}. El runtime no fue instalado. Detalle: {last_error}"
    )


def _safe_target(root: Path, name: str) -> Path:
    target = (root / name).resolve()
    root_resolved = root.resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise InvalidInputError("El paquete de runtime contiene una ruta insegura.")
    return target


def _extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if archive.suffix.casefold() == ".zip":
        with zipfile.ZipFile(archive) as bundle:
            for info in bundle.infolist():
                _safe_target(destination, info.filename)
                mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(mode):
                    raise InvalidInputError("El paquete ZIP del runtime contiene un enlace simbólico no permitido.")
            bundle.extractall(destination)
        return
    if archive.name.endswith(".tar.gz") or archive.suffix.casefold() in {".tgz", ".tar"}:
        with tarfile.open(archive) as bundle:
            members = bundle.getmembers()
            for member in members:
                _safe_target(destination, member.name)
            if hasattr(tarfile, "data_filter"):
                bundle.extractall(destination, members=members, filter="data")
            else:
                if any(member.issym() or member.islnk() or member.isdev() for member in members):
                    raise InvalidInputError(
                        "El paquete TAR del runtime contiene enlaces o dispositivos no permitidos "
                        "por este Python."
                    )
                bundle.extractall(destination, members=members)
        return
    raise InvalidInputError(f"Formato de runtime no reconocido: {archive.name}")


def _find_server(root: Path) -> Path:
    names = ("llama-server.exe", "llama-server") if os.name == "nt" else ("llama-server", "llama-server.exe")
    matches: list[Path] = []
    for name in names:
        matches.extend(path for path in root.rglob(name) if path.is_file())
    if not matches:
        raise RuntimeUnavailableError("El paquete de llama.cpp no contiene llama-server.")
    matches.sort(key=lambda item: (len(item.parts), str(item)))
    executable = matches[0]
    if os.name != "nt":
        executable.chmod(executable.stat().st_mode | 0o111)
    return executable


def _write_marker(root: Path, *, package: RuntimePackage, executable: Path, source: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "runtime": "llama.cpp",
        "tag": PINNED_LLAMA_TAG,
        "build": PINNED_LLAMA_BUILD,
        "commit": PINNED_LLAMA_COMMIT,
        "system": package.system,
        "machine": package.machine,
        "variant": package.variant,
        "source": source,
        "executable": str(executable.resolve().relative_to(root.resolve())),
        "assets": [
            {"filename": asset.filename, "sha256": asset.sha256, "url": asset.url}
            for asset in package.assets
        ],
    }
    (root / _MARKER).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def _build_linux_nvidia(root: Path, package: RuntimePackage) -> dict[str, object]:
    required = [name for name in ("git", "cmake") if shutil.which(name) is None]
    if shutil.which("nvcc") is None:
        required.append("nvcc (CUDA Toolkit)")
    if required:
        raise RuntimeUnavailableError(
            "Para preparar el runtime NVIDIA en Linux faltan: " + ", ".join(required) + "."
        )
    src = root / "src"
    build = root / "build"
    root.mkdir(parents=True, exist_ok=True)
    if not (src / ".git").is_dir():
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", PINNED_LLAMA_TAG, "https://github.com/ggml-org/llama.cpp.git", str(src)],
            check=True,
        )
    subprocess.run(["git", "-C", str(src), "fetch", "--depth", "1", "origin", "tag", PINNED_LLAMA_TAG], check=True)
    subprocess.run(["git", "-C", str(src), "checkout", "--detach", PINNED_LLAMA_TAG], check=True)
    actual = subprocess.run(
        ["git", "-C", str(src), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if actual != PINNED_LLAMA_COMMIT:
        raise RuntimeUnavailableError(
            f"El tag {PINNED_LLAMA_TAG} resolvió a {actual}, no al commit fijado {PINNED_LLAMA_COMMIT}."
        )
    subprocess.run(
        [
            "cmake",
            "-S",
            str(src),
            "-B",
            str(build),
            "-DGGML_CUDA=ON",
            "-DGGML_NATIVE=OFF",
            "-DGGML_CUDA_FA_QUANTS=q4_0-q4_0;q8_0-q8_0;f16-f16;bf16-bf16",
        ],
        check=True,
    )
    subprocess.run(
        ["cmake", "--build", str(build), "--config", "Release", "--target", "llama-server", "-j", str(os.cpu_count() or 2)],
        check=True,
    )
    executable = _find_server(build)
    return _write_marker(root, package=package, executable=executable, source="source-build")


def install_runtime(*, variant: str = "auto", force: bool = False) -> dict[str, object]:
    system = normalize_system()
    machine = normalize_machine(system=system)
    effective_variant = recommended_variant(system, machine) if variant == "auto" else variant
    package = runtime_package(system, machine, effective_variant)
    if package is None:
        raise RuntimeUnavailableError(
            f"No hay un runtime preparado para {system}/{machine} con variante {effective_variant}."
        )
    root = runtime_home()
    if root.exists() and force:
        shutil.rmtree(root)
    current = managed_runtime_metadata(root)
    current_executable = managed_runtime_executable(root)
    if current and current_executable and current.get("variant") == effective_variant:
        return {**current, "status": "already_installed", "root": str(root)}
    if root.exists() and any(root.iterdir()):
        raise RuntimeUnavailableError(
            f"Ya existe contenido en {root}. Usá --force para reemplazar el runtime administrado."
        )
    if package.source_build:
        try:
            marker = _build_linux_nvidia(root, package)
        except subprocess.CalledProcessError as exc:
            raise RuntimeUnavailableError(
                f"No se pudo compilar llama.cpp para NVIDIA (comando: {' '.join(map(str, exc.cmd))})."
            ) from exc
        return {**marker, "status": "installed", "root": str(root)}

    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aw_ai_runtime_") as temp_name:
        temp = Path(temp_name)
        for asset in package.assets:
            archive = temp / asset.filename
            _download(asset, archive)
            _extract(archive, root)
    executable = _find_server(root)
    marker = _write_marker(root, package=package, executable=executable, source="upstream-release")
    return {**marker, "status": "installed", "root": str(root)}


def runtime_installation_report() -> dict[str, object]:
    root = runtime_home()
    metadata = managed_runtime_metadata(root)
    executable = managed_runtime_executable(root)
    return {
        "root": str(root),
        "installed": executable is not None,
        "executable": str(executable) if executable is not None else None,
        "metadata": metadata,
        "recommended_variant": recommended_variant(),
        "system": normalize_system(),
        "machine": normalize_machine(system=normalize_system()),
    }
