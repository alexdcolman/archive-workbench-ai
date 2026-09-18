from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .exp01 import SelectedAsset
from .protocol import Request


@dataclass(slots=True, frozen=True)
class MockResponse:
    output: dict[str, Any]
    raw_text: str


def infer(asset: SelectedAsset, request: Request) -> MockResponse:
    dimensions = None
    if isinstance(asset.width, int) and isinstance(asset.height, int):
        dimensions = f"{asset.width}×{asset.height}"
    features = [f"tipo:{asset.kind}"]
    if asset.mime_type:
        features.append(f"mime:{asset.mime_type}")
    if dimensions:
        features.append(f"dimensiones:{dimensions}")

    description = f"Salida simulada P0 para {asset.asset_id}."
    if dimensions:
        description += f" El asset declarado mide {dimensions}."

    output = {
        "description": description,
        "visible_text_notes": [],
        "document_features": features,
        "uncertainties": [
            "Resultado simulado: P0 valida el protocolo y no ejecuta inferencia multimodal real."
        ],
    }
    raw_text = (
        "MOCK vision_describe/0.1\n"
        f"target={asset.asset_id}\n"
        f"kind={asset.kind}\n"
        f"seed={request.seed}\n"
    )
    return MockResponse(output=output, raw_text=raw_text)
