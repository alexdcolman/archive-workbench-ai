from __future__ import annotations

import json
import posixpath
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from . import PROTOCOL_VERSION, __version__
from .errors import InvalidInputError
from .hashing import sha256_bytes, sha256_path

HANDOFF_PACKAGE_TYPE = "archive_workbench_ai_result_handoff"
HANDOFF_SCHEMA_VERSION = "0.1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_member(name: str) -> bool:
    pure = PurePosixPath(name)
    if pure.is_absolute() or ".." in pure.parts:
        return False
    normalized = posixpath.normpath(name)
    return normalized != ".." and not normalized.startswith("../")


def _load_zip_json(archive: zipfile.ZipFile, member: str, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(archive.read(member))
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise InvalidInputError(f"{label} no contiene {member} JSON válido") from exc
    if not isinstance(payload, dict):
        raise InvalidInputError(f"{label} contiene {member} inválido")
    return payload


def _load_jsonl(payload: bytes, *, label: str) -> list[dict[str, Any]]:
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise InvalidInputError(f"{label} no está codificado en UTF-8") from exc
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise InvalidInputError(f"{label} contiene JSON inválido en línea {line_number}") from exc
        if not isinstance(row, dict):
            raise InvalidInputError(f"{label} contiene una fila inválida")
        rows.append(row)
    return rows


def build_handoff_bundle(*, input_path: Path, result_path: Path, output_path: Path) -> dict[str, Any]:
    if not input_path.is_file():
        raise InvalidInputError(f"No existe EXP-01: {input_path}")
    if not result_path.is_file():
        raise InvalidInputError(f"No existe result bundle: {result_path}")

    input_sha = sha256_path(input_path)
    result_sha = sha256_path(result_path)

    try:
        with zipfile.ZipFile(input_path) as exp_zip:
            exp_names = exp_zip.namelist()
            if any(not _safe_member(name) for name in exp_names):
                raise InvalidInputError("EXP-01 contiene rutas inseguras")
            exp_manifest = _load_zip_json(exp_zip, "manifest.json", label="EXP-01")
            if exp_manifest.get("package_type") != "archive_workbench_text_and_images":
                raise InvalidInputError("El input no es EXP-01 de Archive Workbench")
            assets = exp_manifest.get("assets")
            if not isinstance(assets, list):
                raise InvalidInputError("EXP-01 no declara assets válidos")
            asset_by_id: dict[str, dict[str, Any]] = {}
            for asset in assets:
                if not isinstance(asset, dict):
                    raise InvalidInputError("EXP-01 contiene asset inválido")
                asset_id = asset.get("asset_id")
                if not isinstance(asset_id, str) or not asset_id:
                    raise InvalidInputError("EXP-01 contiene asset sin asset_id")
                asset_by_id[asset_id] = asset
    except zipfile.BadZipFile as exc:
        raise InvalidInputError("EXP-01 no es un ZIP válido") from exc

    try:
        with zipfile.ZipFile(result_path) as result_zip:
            result_names = result_zip.namelist()
            if any(not _safe_member(name) for name in result_names):
                raise InvalidInputError("Result bundle contiene rutas inseguras")
            result_manifest = _load_zip_json(result_zip, "manifest.json", label="result bundle")
            if result_manifest.get("protocol") != PROTOCOL_VERSION:
                raise InvalidInputError("Result bundle usa un protocolo no soportado")
            if result_manifest.get("status") != "complete":
                raise InvalidInputError("Result bundle no está completo")
            if result_manifest.get("input_sha256") != input_sha:
                raise InvalidInputError("Result bundle no corresponde al EXP-01 indicado")
            try:
                items_payload = result_zip.read("results/items.jsonl")
            except KeyError as exc:
                raise InvalidInputError("Result bundle no contiene results/items.jsonl") from exc
            result_items = _load_jsonl(items_payload, label="results/items.jsonl")
    except zipfile.BadZipFile as exc:
        raise InvalidInputError("Result bundle no es un ZIP válido") from exc

    proposals: list[dict[str, Any]] = []
    request_id = result_manifest.get("request_id")
    model = result_manifest.get("model") if isinstance(result_manifest.get("model"), dict) else {}
    runtime = result_manifest.get("runtime") if isinstance(result_manifest.get("runtime"), dict) else {}
    prompt = result_manifest.get("prompt") if isinstance(result_manifest.get("prompt"), dict) else {}

    for row in result_items:
        if row.get("status") != "ok":
            continue
        target_id = row.get("target_id")
        target_type = row.get("target_type")
        result_id = row.get("result_id")
        if not isinstance(target_id, str) or target_id not in asset_by_id:
            raise InvalidInputError(f"Resultado refiere a target inexistente en EXP-01: {target_id!r}")
        if not isinstance(result_id, str) or not result_id:
            raise InvalidInputError("Resultado sin result_id válido")
        asset = asset_by_id[target_id]
        if asset.get("kind") != target_type:
            raise InvalidInputError(f"Tipo incompatible para target {target_id}")

        proposal_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{result_sha}:{result_id}:{target_id}"))
        proposals.append(
            {
                "proposal_id": proposal_id,
                "result_id": result_id,
                "request_id": request_id,
                "target_id": target_id,
                "target_type": target_type,
                "digital_object_id": asset.get("digital_object_id"),
                "page_number": asset.get("page_number"),
                "source_key": asset.get("source_key"),
                "original_filename": asset.get("original_filename"),
                "asset_path": asset.get("path"),
                "output_schema_id": row.get("output_schema_id"),
                "output": row.get("output"),
                "warnings": row.get("warnings", []),
                "provenance": {
                    "exp01_sha256": input_sha,
                    "result_bundle_sha256": result_sha,
                    "plugin": result_manifest.get("plugin"),
                    "model": model,
                    "runtime": runtime,
                    "prompt": prompt,
                },
            }
        )

    if not proposals:
        raise InvalidInputError("Result bundle no contiene resultados OK para transferir")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aw_ai_handoff_") as tmp_name:
        root = Path(tmp_name)
        (root / "results").mkdir()
        proposals_path = root / "results" / "proposals.jsonl"
        proposals_path.write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in proposals),
            encoding="utf-8",
        )
        proposals_sha = sha256_path(proposals_path)
        manifest = {
            "package_type": HANDOFF_PACKAGE_TYPE,
            "schema_version": HANDOFF_SCHEMA_VERSION,
            "protocol": PROTOCOL_VERSION,
            "created_at": _utc_now(),
            "producer": {"id": "archive-workbench-ai", "version": __version__},
            "request_id": request_id,
            "source": {
                "exp01_sha256": input_sha,
                "result_bundle_sha256": result_sha,
                "exp01_schema_version": exp_manifest.get("schema_version"),
            },
            "model": model,
            "runtime": runtime,
            "prompt": prompt,
            "policy": {
                "application": "proposed_only",
                "automatic_apply": False,
                "human_review_required": True,
            },
            "proposals_path": "results/proposals.jsonl",
            "proposals_sha256": proposals_sha,
            "proposal_count": len(proposals),
        }
        (root / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        temporary = output_path.with_name(output_path.name + ".tmp")
        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.write(root / "manifest.json", "manifest.json")
                archive.write(proposals_path, "results/proposals.jsonl")
            temporary.replace(output_path)
        finally:
            temporary.unlink(missing_ok=True)
    return manifest


def inspect_handoff_bundle(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise InvalidInputError(f"No existe handoff bundle: {path}")
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if any(not _safe_member(name) for name in names):
                raise InvalidInputError("Handoff contiene rutas inseguras")
            manifest = _load_zip_json(archive, "manifest.json", label="handoff")
            if manifest.get("package_type") != HANDOFF_PACKAGE_TYPE:
                raise InvalidInputError("El ZIP no es un handoff AI-01")
            if manifest.get("schema_version") != HANDOFF_SCHEMA_VERSION:
                raise InvalidInputError("Schema de handoff no soportado")
            proposals_path = manifest.get("proposals_path")
            expected_sha = manifest.get("proposals_sha256")
            if not isinstance(proposals_path, str) or proposals_path not in names or not _safe_member(proposals_path):
                raise InvalidInputError("Handoff no contiene proposals válidas")
            payload = archive.read(proposals_path)
            if not isinstance(expected_sha, str) or sha256_bytes(payload) != expected_sha:
                raise InvalidInputError("SHA-256 de proposals incorrecto")
            proposals = _load_jsonl(payload, label="results/proposals.jsonl")
            if manifest.get("proposal_count") != len(proposals):
                raise InvalidInputError("proposal_count no coincide con proposals")
    except zipfile.BadZipFile as exc:
        raise InvalidInputError("Handoff no es un ZIP válido") from exc

    return {
        "status": "ok",
        "path": str(path),
        "sha256": sha256_path(path),
        "package_type": manifest["package_type"],
        "schema_version": manifest["schema_version"],
        "proposal_count": len(proposals),
        "request_id": manifest.get("request_id"),
        "model_id": (manifest.get("model") or {}).get("model_id") if isinstance(manifest.get("model"), dict) else None,
        "policy": manifest.get("policy"),
    }
