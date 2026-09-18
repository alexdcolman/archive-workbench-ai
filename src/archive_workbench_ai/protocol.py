from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from . import PROTOCOL_VERSION
from .errors import IncompatibleProtocolError, InvalidRequestError

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_TARGET_TYPES = {"page", "region", "figure"}
_ALLOWED_PROFILES = {"auto", "L12", "H24"}


@dataclass(slots=True, frozen=True)
class Target:
    target_id: str
    target_type: str


@dataclass(slots=True, frozen=True)
class Request:
    raw: dict[str, Any]
    request_id: str
    created_at: str
    input_sha256: str
    targets: tuple[Target, ...]
    hardware_profile: str
    seed: int
    max_output_tokens: int
    temperature: float


def _require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidRequestError(f"{name} debe ser un objeto JSON")
    return value


def _require_exact_keys(obj: dict[str, Any], name: str, required: set[str]) -> None:
    missing = required - obj.keys()
    extra = obj.keys() - required
    if missing:
        raise InvalidRequestError(f"Faltan campos en {name}: {', '.join(sorted(missing))}")
    if extra:
        raise InvalidRequestError(f"Campos no admitidos en {name}: {', '.join(sorted(extra))}")


def _validate_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise InvalidRequestError("created_at debe ser una fecha RFC3339")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidRequestError("created_at no es una fecha RFC3339 válida") from exc
    return value


def load_request(path: Path) -> Request:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InvalidRequestError(f"No existe request.json: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidRequestError(f"No se pudo leer request.json: {exc}") from exc

    root = _require_dict(raw, "request")
    _require_exact_keys(
        root,
        "request",
        {"protocol", "request_id", "created_at", "task", "input", "targets", "execution", "generation", "output"},
    )

    if root["protocol"] != PROTOCOL_VERSION:
        raise IncompatibleProtocolError(
            f"Protocolo no soportado: {root['protocol']!r}; esperado {PROTOCOL_VERSION!r}"
        )

    try:
        request_id = str(uuid.UUID(str(root["request_id"])))
    except (ValueError, AttributeError) as exc:
        raise InvalidRequestError("request_id debe ser un UUID válido") from exc

    created_at = _validate_timestamp(root["created_at"])

    task = _require_dict(root["task"], "task")
    _require_exact_keys(task, "task", {"id", "version"})
    if task != {"id": "vision_describe", "version": "0.1"}:
        raise IncompatibleProtocolError("P0 sólo admite task vision_describe/0.1")

    input_obj = _require_dict(root["input"], "input")
    _require_exact_keys(input_obj, "input", {"bundle_type", "sha256"})
    if input_obj["bundle_type"] != "exp01":
        raise IncompatibleProtocolError("P0 sólo admite bundle_type exp01")
    input_sha256 = input_obj["sha256"]
    if not isinstance(input_sha256, str) or not _HEX64.fullmatch(input_sha256):
        raise InvalidRequestError("input.sha256 debe contener 64 caracteres hexadecimales en minúscula")

    targets_raw = root["targets"]
    if not isinstance(targets_raw, list) or not 1 <= len(targets_raw) <= 3:
        raise InvalidRequestError("targets debe contener entre 1 y 3 elementos")
    targets: list[Target] = []
    seen: set[str] = set()
    for index, item in enumerate(targets_raw):
        target = _require_dict(item, f"targets[{index}]")
        _require_exact_keys(target, f"targets[{index}]", {"target_id", "target_type"})
        target_id = target["target_id"]
        target_type = target["target_type"]
        if not isinstance(target_id, str) or not target_id.strip():
            raise InvalidRequestError(f"targets[{index}].target_id debe ser texto no vacío")
        if target_type not in _ALLOWED_TARGET_TYPES:
            raise InvalidRequestError(f"targets[{index}].target_type no es válido")
        if target_id in seen:
            raise InvalidRequestError(f"Target repetido: {target_id}")
        seen.add(target_id)
        targets.append(Target(target_id=target_id, target_type=target_type))

    execution = _require_dict(root["execution"], "execution")
    _require_exact_keys(execution, "execution", {"network_policy", "hardware_profile", "seed"})
    if execution["network_policy"] != "offline_required":
        raise IncompatibleProtocolError("P0 exige network_policy=offline_required")
    hardware_profile = execution["hardware_profile"]
    if hardware_profile not in _ALLOWED_PROFILES:
        raise InvalidRequestError("hardware_profile debe ser auto, L12 o H24")
    seed = execution["seed"]
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise InvalidRequestError("execution.seed debe ser entero")

    generation = _require_dict(root["generation"], "generation")
    _require_exact_keys(generation, "generation", {"max_output_tokens", "temperature"})
    max_output_tokens = generation["max_output_tokens"]
    if isinstance(max_output_tokens, bool) or not isinstance(max_output_tokens, int) or max_output_tokens <= 0:
        raise InvalidRequestError("generation.max_output_tokens debe ser entero positivo")
    temperature = generation["temperature"]
    if isinstance(temperature, bool) or not isinstance(temperature, (int, float)) or not 0.0 <= float(temperature) <= 2.0:
        raise InvalidRequestError("generation.temperature debe estar entre 0 y 2")

    output = _require_dict(root["output"], "output")
    _require_exact_keys(output, "output", {"schema_id"})
    if output["schema_id"] != "vision_describe/0.1":
        raise IncompatibleProtocolError("P0 sólo produce vision_describe/0.1")

    return Request(
        raw=root,
        request_id=request_id,
        created_at=created_at,
        input_sha256=input_sha256,
        targets=tuple(targets),
        hardware_profile=hardware_profile,
        seed=seed,
        max_output_tokens=max_output_tokens,
        temperature=float(temperature),
    )
