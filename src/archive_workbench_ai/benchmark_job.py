from __future__ import annotations

import io
import json
import tempfile
import uuid
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from PIL import Image, ImageOps, UnidentifiedImageError

from . import PROTOCOL_VERSION, __version__
from .errors import InvalidInputError
from .hashing import sha256_bytes, sha256_path

_JOB_SCHEMA_VERSION = "1.0"
_JOB_PACKAGE_TYPE = "archive_workbench_ai01_benchmark_job"
_EXP_PACKAGE_TYPE = "archive_workbench_text_and_images"
_ALLOWED_PROFILES = {"L12", "H24"}


def _downloads_dir() -> Path:
    root = Path.home() / "Downloads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _png_payload(path: Path) -> tuple[bytes, int, int, str]:
    if not path.is_file():
        raise InvalidInputError(f"No existe la imagen para benchmark: {path}")
    try:
        with Image.open(path) as opened:
            frame_count = int(getattr(opened, "n_frames", 1))
            if frame_count != 1:
                raise InvalidInputError(
                    f"La imagen tiene {frame_count} páginas/cuadros: {path.name}. "
                    "Prepará una imagen por página para conservar targets inequívocos."
                )
            source_format = (opened.format or path.suffix.lstrip(".") or "unknown").upper()
            image = ImageOps.exif_transpose(opened).copy()
    except InvalidInputError:
        raise
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidInputError(f"No se pudo abrir la imagen para benchmark: {path}") from exc

    if image.mode not in {"1", "L", "LA", "P", "RGB", "RGBA"}:
        image = image.convert("RGB")
    width, height = image.size
    if width <= 0 or height <= 0:
        raise InvalidInputError(f"Dimensiones inválidas en la imagen: {path}")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue(), width, height, source_format


def prepare_benchmark_job(
    *,
    image_paths: list[Path],
    hardware_profile: str,
    max_output_tokens: int = 512,
    output_path: Path | None = None,
) -> dict[str, Any]:
    if not 1 <= len(image_paths) <= 3:
        raise InvalidInputError("El benchmark admite entre 1 y 3 imágenes por job")
    if hardware_profile not in _ALLOWED_PROFILES:
        raise InvalidInputError("hardware_profile debe ser L12 o H24")
    if isinstance(max_output_tokens, bool) or not isinstance(max_output_tokens, int) or max_output_tokens <= 0:
        raise InvalidInputError("max_output_tokens debe ser un entero positivo")

    prepared: list[dict[str, Any]] = []
    for index, source_path in enumerate(image_paths, start=1):
        source_path = source_path.expanduser().resolve()
        png, width, height, source_format = _png_payload(source_path)
        prepared.append(
            {
                "index": index,
                "source_name": source_path.name,
                "source_sha256": sha256_path(source_path),
                "source_byte_size": source_path.stat().st_size,
                "source_format": source_format,
                "png": png,
                "png_sha256": sha256_bytes(png),
                "png_byte_size": len(png),
                "width": width,
                "height": height,
            }
        )

    corpus_state = sha256_bytes(
        json.dumps(
            [
                {
                    "source_sha256": item["source_sha256"],
                    "width": item["width"],
                    "height": item["height"],
                }
                for item in prepared
            ],
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )

    assets: list[dict[str, Any]] = []
    targets: list[dict[str, str]] = []
    for item in prepared:
        target_id = f"page:ai01-p2-expanded:{item['index']}"
        member = f"images/pages/page_{item['index']:04d}.png"
        assets.append(
            {
                "asset_id": target_id,
                "kind": "page",
                "path": member,
                "sha256": item["png_sha256"],
                "byte_size": item["png_byte_size"],
                "mime_type": "image/png",
                "width": item["width"],
                "height": item["height"],
            }
        )
        targets.append({"target_id": target_id, "target_type": "page"})

    exp_manifest = {
        "schema_version": "1.0",
        "package_type": _EXP_PACKAGE_TYPE,
        "archive_workbench_version": "external-benchmark-input",
        "project_id": "ai01-p2-expanded-benchmark",
        "profile": {"purpose": "AI-01 P2 expanded benchmark"},
        "corpus_state_sha256": corpus_state,
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
            "sha256": sha256_bytes(b""),
        },
        "context": {
            "objects_path": "context/objects.jsonl",
            "objects_sha256": sha256_bytes(b""),
            "object_count": 0,
            "pages_path": "context/pages.jsonl",
            "pages_sha256": sha256_bytes(b""),
            "page_count": 0,
            "documents_path": "context/documents.jsonl",
            "documents_sha256": sha256_bytes(b""),
            "document_count": 0,
        },
        "assets": assets,
        "asset_counts": {"pages": len(assets), "regions": 0, "figures": 0},
    }

    exp_buffer = io.BytesIO()
    with zipfile.ZipFile(exp_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "manifest.json",
            json.dumps(exp_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        for item, asset in zip(prepared, assets, strict=True):
            archive.writestr(asset["path"], item["png"])
        for member in (
            "text/records.jsonl",
            "context/objects.jsonl",
            "context/pages.jsonl",
            "context/documents.jsonl",
        ):
            archive.writestr(member, b"")
    exp_payload = exp_buffer.getvalue()
    exp_sha256 = sha256_bytes(exp_payload)

    request = {
        "protocol": PROTOCOL_VERSION,
        "request_id": str(uuid.uuid4()),
        "created_at": _now(),
        "task": {"id": "vision_describe", "version": "0.1"},
        "input": {"bundle_type": "exp01", "sha256": exp_sha256},
        "targets": targets,
        "execution": {
            "network_policy": "offline_required",
            "hardware_profile": hardware_profile,
            "seed": 0,
        },
        "generation": {"max_output_tokens": max_output_tokens, "temperature": 0.0},
        "output": {"schema_id": "vision_describe/0.1"},
    }
    request_payload = (json.dumps(request, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")

    job_manifest = {
        "schema_version": _JOB_SCHEMA_VERSION,
        "package_type": _JOB_PACKAGE_TYPE,
        "plugin_version": __version__,
        "protocol": PROTOCOL_VERSION,
        "created_at": _now(),
        "hardware_profile": hardware_profile,
        "max_output_tokens": max_output_tokens,
        "request_member": "request.json",
        "input_member": "exp01.zip",
        "input_sha256": exp_sha256,
        "sources": [
            {
                "target_id": targets[item["index"] - 1]["target_id"],
                "source_name": item["source_name"],
                "source_sha256": item["source_sha256"],
                "source_byte_size": item["source_byte_size"],
                "source_format": item["source_format"],
                "prepared_mime_type": "image/png",
                "prepared_sha256": item["png_sha256"],
                "prepared_byte_size": item["png_byte_size"],
                "width": item["width"],
                "height": item["height"],
            }
            for item in prepared
        ],
    }

    output_path = output_path or (_downloads_dir() / f"AWAI_BENCHMARK_JOB_{_stamp()}.zip")
    output_path = output_path.expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(output_path.name + ".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "job_manifest.json",
            json.dumps(job_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        archive.writestr("request.json", request_payload)
        archive.writestr("exp01.zip", exp_payload)
    temporary.replace(output_path)

    return {
        "status": "complete",
        "output": str(output_path),
        "hardware_profile": hardware_profile,
        "targets": len(prepared),
        "input_sha256": exp_sha256,
        "sources": job_manifest["sources"],
    }


def _safe_job_member(name: Any) -> str:
    if not isinstance(name, str) or not name or name.startswith("/") or ".." in Path(name).parts:
        raise InvalidInputError("Benchmark job contiene una ruta interna inválida")
    return name


@contextmanager
def extracted_benchmark_job(job_path: Path) -> Iterator[tuple[Path, Path]]:
    job_path = job_path.expanduser()
    if not job_path.is_file():
        raise InvalidInputError(f"No existe benchmark job: {job_path}")
    try:
        with zipfile.ZipFile(job_path) as archive:
            if "job_manifest.json" not in archive.namelist():
                raise InvalidInputError("Benchmark job no contiene job_manifest.json")
            try:
                manifest = json.loads(archive.read("job_manifest.json").decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise InvalidInputError("job_manifest.json no es JSON válido") from exc
            if manifest.get("schema_version") != _JOB_SCHEMA_VERSION or manifest.get("package_type") != _JOB_PACKAGE_TYPE:
                raise InvalidInputError("ZIP no es un benchmark job AI-01 compatible")
            request_member = _safe_job_member(manifest.get("request_member"))
            input_member = _safe_job_member(manifest.get("input_member"))
            names = set(archive.namelist())
            if request_member not in names or input_member not in names:
                raise InvalidInputError("Benchmark job no contiene request/input declarados")
            request_payload = archive.read(request_member)
            input_payload = archive.read(input_member)
            expected_input_sha = manifest.get("input_sha256")
            if not isinstance(expected_input_sha, str) or sha256_bytes(input_payload) != expected_input_sha:
                raise InvalidInputError("SHA-256 de exp01.zip no coincide con job_manifest.json")
    except zipfile.BadZipFile as exc:
        raise InvalidInputError("Benchmark job no es un ZIP válido") from exc

    with tempfile.TemporaryDirectory(prefix="aw_ai_benchmark_job_") as tmp_name:
        root = Path(tmp_name)
        request_path = root / "request.json"
        input_path = root / "exp01.zip"
        request_path.write_bytes(request_payload)
        input_path.write_bytes(input_payload)
        yield request_path, input_path
