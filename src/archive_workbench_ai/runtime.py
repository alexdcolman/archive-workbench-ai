from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Sequence

from .runtime_catalog import PINNED_LLAMA_BUILD, PINNED_LLAMA_COMMIT, PINNED_LLAMA_TAG


@dataclass(frozen=True, slots=True)
class RuntimeCommand:
    argv_prefix: tuple[str, ...]
    executable: str
    mode: str
    version_text: str | None
    build_number: int | None
    revision: str | None
    status: str


@dataclass(frozen=True, slots=True)
class RuntimeProbeFailure:
    executable: str
    mode: str
    returncode: int | None
    detail: str


@dataclass(frozen=True, slots=True)
class RuntimeDetection:
    runtime: RuntimeCommand | None
    failures: tuple[RuntimeProbeFailure, ...]


def _version_probe(argv: Sequence[str]) -> tuple[str | None, int | None, str | None]:
    try:
        result = subprocess.run([*argv, "--version"], capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, None, str(exc)
    text = (result.stdout + "\n" + result.stderr).strip() or None
    if result.returncode != 0:
        return text, result.returncode, text or f"llama.cpp terminó con código {result.returncode}"
    return text, result.returncode, None


def _version_text(argv: Sequence[str]) -> str | None:
    text, returncode, error = _version_probe(argv)
    if returncode != 0 or error is not None:
        return None
    return text


def _parse_build(text: str | None) -> tuple[int | None, str | None]:
    if not text:
        return None, None
    build = None
    revision = None
    # llama.cpp may print a semantic version such as ``version: 0.4.0-dev``
    # plus an internal ``build 1`` counter. Neither identifies release tag
    # b10903. Only accept a release-shaped bNNNN tag or a 4-6 digit legacy
    # build/version number.
    for pattern in (
        r"\bb(\d{4,6})\b",
        r"\bbuild(?:[ _-]?number)?[: =]+(\d{4,6})\b",
        r"\bversion[: =]+(\d{4,6})\b",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            build = int(match.group(1))
            break
    match = re.search(r"\b([0-9a-f]{7,40})\b", text, re.IGNORECASE)
    if match:
        revision = match.group(1).lower()
    return build, revision


def _validation_status(build: int | None, revision: str | None) -> str:
    # The pinned commit is the strongest identity signal. Current llama.cpp
    # version output does not necessarily expose the release tag/build number.
    if revision and (revision.startswith(PINNED_LLAMA_COMMIT) or PINNED_LLAMA_COMMIT.startswith(revision)):
        return "pinned"
    if build is None:
        return "unverified"
    if build < PINNED_LLAMA_BUILD:
        return "too_old"
    if build == PINNED_LLAMA_BUILD:
        return "pinned"
    return "newer_unverified"


def detect_runtime_detailed() -> RuntimeDetection:
    explicit = os.environ.get("AW_AI_LLAMA_SERVER") or os.environ.get("AW_AI01_LLAMA_SERVER")
    candidates: list[tuple[tuple[str, ...], str, str]] = []
    if explicit:
        path = str(Path(explicit).expanduser())
        candidates.append(((path,), path, "llama-server"))
    try:
        from .runtime_manager import managed_runtime_executable

        managed = managed_runtime_executable()
    except Exception:
        managed = None
    if managed is not None:
        path = str(managed)
        candidates.append(((path,), path, "llama-server"))
    server = shutil.which("llama-server")
    if server:
        candidates.append(((server,), server, "llama-server"))
    llama = shutil.which("llama")
    if llama:
        candidates.append(((llama, "serve"), llama, "llama-serve"))

    failures: list[RuntimeProbeFailure] = []
    seen: set[tuple[str, ...]] = set()
    for prefix, executable, mode in candidates:
        if prefix in seen:
            continue
        seen.add(prefix)
        text, returncode, error = _version_probe((executable,))
        if error is not None:
            failures.append(RuntimeProbeFailure(executable, mode, returncode, error))
            continue
        build, revision = _parse_build(text)
        status = _validation_status(build, revision)
        return RuntimeDetection(RuntimeCommand(prefix, executable, mode, text, build, revision, status), tuple(failures))
    return RuntimeDetection(None, tuple(failures))


def detect_runtime() -> RuntimeCommand | None:
    return detect_runtime_detailed().runtime


def gpu_info() -> list[dict[str, object]]:
    smi = shutil.which("nvidia-smi")
    if not smi:
        return []
    try:
        result = subprocess.run(
            [smi, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    rows = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) >= 3:
            try:
                memory_mib: int | None = int(parts[1])
            except ValueError:
                memory_mib = None
            rows.append({"name": parts[0], "memory_total_mib": memory_mib, "driver_version": parts[2]})
    return rows
