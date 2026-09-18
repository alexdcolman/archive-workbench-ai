from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import PROTOCOL_VERSION
from .catalog import ModelSpec
from .errors import InvalidInputError
from .exp01 import list_exp01_targets, load_selected_assets
from .handoff import build_handoff_bundle
from .hashing import sha256_path
from .protocol import Request, Target
from .result_bundle import build_result_bundle

_MAX_REQUEST_TARGETS = 3


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _request_payload(
    *,
    request_id: str,
    input_sha256: str,
    targets: tuple[tuple[str, str], ...],
    hardware_profile: str,
    seed: int,
    max_output_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    return {
        "protocol": PROTOCOL_VERSION,
        "request_id": request_id,
        "created_at": _utc_now(),
        "task": {"id": "vision_describe", "version": "0.1"},
        "input": {"bundle_type": "exp01", "sha256": input_sha256},
        "targets": [
            {"target_id": target_id, "target_type": target_type}
            for target_id, target_type in targets
        ],
        "execution": {
            "network_policy": "offline_required",
            "hardware_profile": hardware_profile,
            "seed": seed,
        },
        "generation": {
            "max_output_tokens": max_output_tokens,
            "temperature": temperature,
        },
        "output": {"schema_id": "vision_describe/0.1"},
    }


def _request_from_payload(payload: dict[str, Any]) -> Request:
    return Request(
        raw=payload,
        request_id=str(payload["request_id"]),
        created_at=str(payload["created_at"]),
        input_sha256=str(payload["input"]["sha256"]),
        targets=tuple(
            Target(
                target_id=str(item["target_id"]),
                target_type=str(item["target_type"]),
            )
            for item in payload["targets"]
        ),
        hardware_profile=str(payload["execution"]["hardware_profile"]),
        seed=int(payload["execution"]["seed"]),
        max_output_tokens=int(payload["generation"]["max_output_tokens"]),
        temperature=float(payload["generation"]["temperature"]),
    )


def analyze_exp01(
    *,
    input_path: Path,
    handoff_output_path: Path,
    model_spec: ModelSpec,
    hardware_profile: str,
    backend: str = "llama_cpp",
    result_output_path: Path | None = None,
    target_types: tuple[str, ...] = ("page",),
    seed: int = 0,
    max_output_tokens: int = 512,
    temperature: float = 0.0,
) -> dict[str, Any]:
    """Analiza todos los targets elegidos y produce un único result/handoff consolidado.

    El límite de tres targets se conserva únicamente en los requests internos 0.1.
    La persona usuaria recibe un único result bundle y un único handoff compatible
    con Archive Workbench P3.
    """

    if hardware_profile not in {"L12", "H24"}:
        raise InvalidInputError("hardware_profile debe ser L12 o H24")
    if backend not in {"llama_cpp", "mock"}:
        raise InvalidInputError("backend debe ser llama_cpp o mock")
    if max_output_tokens <= 0:
        raise InvalidInputError("max_output_tokens debe ser positivo")
    if not 0.0 <= float(temperature) <= 2.0:
        raise InvalidInputError("temperature debe estar entre 0 y 2")

    _manifest, target_refs = list_exp01_targets(
        input_path,
        target_types=target_types,
    )
    if not target_refs:
        labels = ", ".join(target_types)
        raise InvalidInputError(f"EXP-01 no contiene targets de tipo: {labels}")

    input_sha256 = sha256_path(input_path)
    batch_payloads: list[dict[str, Any]] = []
    all_assets = []
    first_request: Request | None = None
    for start in range(0, len(target_refs), _MAX_REQUEST_TARGETS):
        batch = target_refs[start : start + _MAX_REQUEST_TARGETS]
        payload = _request_payload(
            request_id=str(uuid.uuid4()),
            input_sha256=input_sha256,
            targets=batch,
            hardware_profile=hardware_profile,
            seed=seed,
            max_output_tokens=max_output_tokens,
            temperature=float(temperature),
        )
        request = _request_from_payload(payload)
        if first_request is None:
            first_request = request
        _exp_manifest, assets = load_selected_assets(input_path, request)
        all_assets.extend(assets)
        batch_payloads.append(payload)

    assert first_request is not None
    analysis_id = str(uuid.uuid4())
    run_request = replace(first_request, request_id=analysis_id)
    result_path = result_output_path or handoff_output_path.with_name(
        handoff_output_path.stem + ".result.zip"
    )
    result_manifest = build_result_bundle(
        request=run_request,
        input_path=input_path,
        selected_assets=tuple(all_assets),
        output_path=result_path,
        backend=backend,
        model_spec=model_spec,
        result_request_id=analysis_id,
        batch_requests=tuple(batch_payloads),
    )
    handoff_manifest = build_handoff_bundle(
        input_path=input_path,
        result_path=result_path,
        output_path=handoff_output_path,
    )
    return {
        "status": "ok",
        "analysis_id": analysis_id,
        "input": str(input_path),
        "input_sha256": input_sha256,
        "result": str(result_path),
        "result_sha256": sha256_path(result_path),
        "handoff": str(handoff_output_path),
        "handoff_sha256": sha256_path(handoff_output_path),
        "target_count": len(all_assets),
        "internal_request_count": len(batch_payloads),
        "internal_max_targets": _MAX_REQUEST_TARGETS,
        "target_types": list(target_types),
        "backend": backend,
        "model_id": result_manifest["model"]["model_id"],
        "handoff_schema_version": handoff_manifest["schema_version"],
        "proposal_count": handoff_manifest["proposal_count"],
    }
