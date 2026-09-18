from __future__ import annotations

import json
import posixpath
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .errors import InvalidInputError
from .hashing import sha256_bytes, sha256_path
from .protocol import Request


@dataclass(slots=True, frozen=True)
class SelectedAsset:
    asset_id: str
    kind: str
    path: str
    sha256: str
    byte_size: int
    mime_type: str | None
    width: int | None
    height: int | None
    metadata: dict[str, Any]
    context_objects: tuple[dict[str, Any], ...] = ()


def _safe_member(name: str) -> bool:
    pure = PurePosixPath(name)
    if pure.is_absolute() or ".." in pure.parts:
        return False
    normalized = posixpath.normpath(name)
    return normalized != ".." and not normalized.startswith("../")


def load_selected_assets(input_path: Path, request: Request) -> tuple[dict[str, Any], tuple[SelectedAsset, ...]]:
    if not input_path.is_file():
        raise InvalidInputError(f"No existe el bundle EXP-01: {input_path}")
    actual_bundle_hash = sha256_path(input_path)
    if actual_bundle_hash != request.input_sha256:
        raise InvalidInputError(
            f"SHA-256 del bundle EXP-01 incorrecto: esperado {request.input_sha256}, obtenido {actual_bundle_hash}"
        )

    try:
        with zipfile.ZipFile(input_path) as archive:
            names = archive.namelist()
            unsafe = [name for name in names if not _safe_member(name)]
            if unsafe:
                raise InvalidInputError(f"EXP-01 contiene rutas inseguras: {unsafe[0]}")
            if "manifest.json" not in names:
                raise InvalidInputError("EXP-01 no contiene manifest.json")
            try:
                manifest = json.loads(archive.read("manifest.json"))
            except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise InvalidInputError("manifest.json de EXP-01 no es JSON válido") from exc

            if manifest.get("package_type") != "archive_workbench_text_and_images":
                raise InvalidInputError("El ZIP no es un paquete visual EXP-01 de Archive Workbench")
            schema_version = manifest.get("schema_version")
            if schema_version not in {"1.0", "1.1"}:
                raise InvalidInputError(
                    f"Schema EXP-01 no soportado: {schema_version!r}; esperados '1.0' o '1.1'"
                )
            assets_raw = manifest.get("assets")
            if not isinstance(assets_raw, list):
                raise InvalidInputError("manifest.assets debe ser una lista")
            by_id: dict[str, dict[str, Any]] = {}
            for item in assets_raw:
                if not isinstance(item, dict):
                    raise InvalidInputError("EXP-01 contiene un asset inválido")
                asset_id = item.get("asset_id")
                if not isinstance(asset_id, str) or not asset_id:
                    raise InvalidInputError("EXP-01 contiene un asset sin asset_id")
                if asset_id in by_id:
                    raise InvalidInputError(f"EXP-01 repite asset_id: {asset_id}")
                by_id[asset_id] = item

            context_by_page: dict[tuple[str, int], list[dict[str, Any]]] = {}
            if schema_version == "1.1":
                context = manifest.get("context")
                if not isinstance(context, dict):
                    raise InvalidInputError("EXP-01 1.1 no declara manifest.context")
                geometry_meta = context.get("object_geometry")
                expected_geometry_meta = {
                    "geometry_field": "geometry",
                    "bbox_field": "bbox",
                    "bbox_format": "x_y_width_height",
                    "coordinate_space": "normalized",
                }
                if geometry_meta != expected_geometry_meta:
                    raise InvalidInputError("EXP-01 1.1 declara un contrato de geometría textual no soportado")
                objects_path = context.get("objects_path")
                objects_hash = context.get("objects_sha256")
                if not isinstance(objects_path, str) or objects_path not in names or not _safe_member(objects_path):
                    raise InvalidInputError("EXP-01 1.1 no contiene context/objects.jsonl válido")
                objects_payload = archive.read(objects_path)
                if not isinstance(objects_hash, str) or sha256_bytes(objects_payload) != objects_hash:
                    raise InvalidInputError("SHA-256 de context/objects.jsonl incorrecto")
                try:
                    lines = objects_payload.decode("utf-8").splitlines()
                except UnicodeDecodeError as exc:
                    raise InvalidInputError("context/objects.jsonl no está codificado en UTF-8") from exc
                for line_number, line in enumerate(lines, start=1):
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise InvalidInputError(
                            f"context/objects.jsonl contiene JSON inválido en línea {line_number}"
                        ) from exc
                    if not isinstance(obj, dict):
                        raise InvalidInputError("context/objects.jsonl contiene un objeto inválido")
                    digital_id = obj.get("digital_object_id")
                    page_number = obj.get("page_number")
                    text = obj.get("text")
                    if not isinstance(digital_id, str) or isinstance(page_number, bool) or not isinstance(page_number, int):
                        raise InvalidInputError("Objeto de contexto sin digital_object_id/page_number válidos")
                    if not isinstance(text, str):
                        raise InvalidInputError("Objeto de contexto sin texto canónico válido")
                    bbox = obj.get("bbox")
                    if bbox is not None:
                        if not isinstance(bbox, dict):
                            raise InvalidInputError("bbox textual inválido en EXP-01 1.1")
                        if bbox.get("coordinate_space") != "normalized" or bbox.get("page") != page_number:
                            raise InvalidInputError("bbox textual usa un espacio de coordenadas no soportado")
                        for key in ("x", "y", "width", "height"):
                            value = bbox.get(key)
                            if isinstance(value, bool) or not isinstance(value, (int, float)):
                                raise InvalidInputError(f"bbox textual sin {key} numérico")
                    context_by_page.setdefault((digital_id, page_number), []).append(obj)
                for members in context_by_page.values():
                    members.sort(key=lambda item: (item.get("order_index", 0), str(item.get("object_id", ""))))

            selected: list[SelectedAsset] = []
            for target in request.targets:
                item = by_id.get(target.target_id)
                if item is None:
                    raise InvalidInputError(f"Target no encontrado en EXP-01: {target.target_id}")
                if item.get("kind") != target.target_type:
                    raise InvalidInputError(
                        f"Tipo de target incompatible para {target.target_id}: request={target.target_type}, EXP-01={item.get('kind')}"
                    )
                path = item.get("path")
                expected_hash = item.get("sha256")
                expected_size = item.get("byte_size")
                if not isinstance(path, str) or path not in names or not _safe_member(path):
                    raise InvalidInputError(f"Asset sin archivo válido en EXP-01: {target.target_id}")
                if not isinstance(expected_hash, str) or len(expected_hash) != 64:
                    raise InvalidInputError(f"Asset sin SHA-256 válido: {target.target_id}")
                if isinstance(expected_size, bool) or not isinstance(expected_size, int) or expected_size < 0:
                    raise InvalidInputError(f"Asset sin byte_size válido: {target.target_id}")
                payload = archive.read(path)
                actual_hash = sha256_bytes(payload)
                if actual_hash != expected_hash:
                    raise InvalidInputError(f"SHA-256 interno incorrecto para {target.target_id}")
                if len(payload) != expected_size:
                    raise InvalidInputError(f"byte_size interno incorrecto para {target.target_id}")
                selected.append(
                    SelectedAsset(
                        asset_id=target.target_id,
                        kind=target.target_type,
                        path=path,
                        sha256=expected_hash,
                        byte_size=expected_size,
                        mime_type=item.get("mime_type"),
                        width=item.get("width"),
                        height=item.get("height"),
                        metadata=item,
                        context_objects=tuple(
                            context_by_page.get(
                                (str(item.get("digital_object_id")), int(item.get("page_number"))),
                                [],
                            )
                        )
                        if schema_version == "1.1"
                        and isinstance(item.get("digital_object_id"), str)
                        and isinstance(item.get("page_number"), int)
                        and not isinstance(item.get("page_number"), bool)
                        else (),
                    )
                )
    except zipfile.BadZipFile as exc:
        raise InvalidInputError("El input EXP-01 no es un ZIP válido") from exc

    return manifest, tuple(selected)


def list_exp01_targets(
    input_path: Path,
    *,
    target_types: tuple[str, ...] = ("page",),
) -> tuple[dict[str, Any], tuple[tuple[str, str], ...]]:
    """Lista targets válidos de un EXP-01 sin imponer el límite 1-3 del request 0.1."""
    if not input_path.is_file():
        raise InvalidInputError(f"No existe el bundle EXP-01: {input_path}")
    allowed = {str(value) for value in target_types}
    if not allowed or not allowed.issubset({"page", "region", "figure"}):
        raise InvalidInputError("target_types debe incluir page, region y/o figure")
    try:
        with zipfile.ZipFile(input_path) as archive:
            names = archive.namelist()
            unsafe = [name for name in names if not _safe_member(name)]
            if unsafe:
                raise InvalidInputError(f"EXP-01 contiene rutas inseguras: {unsafe[0]}")
            if "manifest.json" not in names:
                raise InvalidInputError("EXP-01 no contiene manifest.json")
            try:
                manifest = json.loads(archive.read("manifest.json"))
            except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise InvalidInputError("manifest.json de EXP-01 no es JSON válido") from exc
            if not isinstance(manifest, dict):
                raise InvalidInputError("manifest.json de EXP-01 no es un objeto JSON")
            if manifest.get("package_type") != "archive_workbench_text_and_images":
                raise InvalidInputError("El ZIP no es un paquete visual EXP-01 de Archive Workbench")
            if manifest.get("schema_version") not in {"1.0", "1.1"}:
                raise InvalidInputError("Schema EXP-01 no soportado")
            assets = manifest.get("assets")
            if not isinstance(assets, list):
                raise InvalidInputError("manifest.assets debe ser una lista")
            seen: set[str] = set()
            targets: list[tuple[str, str]] = []
            for item in assets:
                if not isinstance(item, dict):
                    raise InvalidInputError("EXP-01 contiene un asset inválido")
                asset_id = item.get("asset_id")
                kind = item.get("kind")
                if not isinstance(asset_id, str) or not asset_id:
                    raise InvalidInputError("EXP-01 contiene un asset sin asset_id")
                if asset_id in seen:
                    raise InvalidInputError(f"EXP-01 repite asset_id: {asset_id}")
                seen.add(asset_id)
                if kind in allowed:
                    targets.append((asset_id, str(kind)))
    except zipfile.BadZipFile as exc:
        raise InvalidInputError("El input EXP-01 no es un ZIP válido") from exc
    return manifest, tuple(targets)
