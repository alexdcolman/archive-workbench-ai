from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import sys


@dataclass(frozen=True, slots=True)
class ModelFile:
    filename: str
    url: str
    sha256: str
    byte_size: int | None
    role: str


@dataclass(frozen=True, slots=True)
class ModelSpec:
    model_id: str
    storage_name: str
    upstream: str
    quantization: str
    files: tuple[ModelFile, ...]
    tasks: tuple[str, ...]
    status: str
    note: str
    hardware_profiles: tuple[str, ...]


MINICPM_V46 = ModelSpec(
    model_id="ggml-org/MiniCPM-V-4.6-GGUF:Q4_K_M",
    storage_name="minicpm-v-4.6-q4_k_m",
    upstream="https://huggingface.co/ggml-org/MiniCPM-V-4.6-GGUF",
    quantization="Q4_K_M + mmproj Q8_0",
    files=(
        ModelFile(
            filename="MiniCPM-V-4.6-Q4_K_M.gguf",
            url="https://huggingface.co/ggml-org/MiniCPM-V-4.6-GGUF/resolve/main/MiniCPM-V-4.6-Q4_K_M.gguf?download=true",
            sha256="b1a5aa76b5ef039c2e579272ea33d4bbed7e79b49bb3ff1efdb23316d6af5199",
            byte_size=529101536,
            role="model",
        ),
        ModelFile(
            filename="mmproj-MiniCPM-V-4.6-Q8_0.gguf",
            url="https://huggingface.co/ggml-org/MiniCPM-V-4.6-GGUF/resolve/main/mmproj-MiniCPM-V-4.6-Q8_0.gguf?download=true",
            sha256="3d8249cdd0e1cb699644eb021fbcc04320aad89fa5dc9234ef94db0846556581",
            byte_size=727954528,
            role="mmproj",
        ),
    ),
    tasks=("vision_describe",),
    status="baseline",
    note="Baseline técnico validado en P1 sobre RTX 3090; no implica recomendación de calidad.",
    hardware_profiles=("L12", "H24"),
)


GEMMA4_E4B_Q4 = ModelSpec(
    model_id="ggml-org/gemma-4-E4B-it-GGUF:Q4_0",
    storage_name="gemma-4-e4b-it-q4_0",
    upstream="https://huggingface.co/ggml-org/gemma-4-E4B-it-GGUF",
    quantization="Q4_0 + mmproj Q8_0",
    files=(
        ModelFile(
            filename="gemma-4-E4B-it-Q4_0.gguf",
            url="https://huggingface.co/ggml-org/gemma-4-E4B-it-GGUF/resolve/main/gemma-4-E4B-it-Q4_0.gguf?download=true",
            sha256="a555b900214b477d8880e7832e0b8925e139b0159640036b09fe472b6f2097f2",
            byte_size=4590807392,
            role="model",
        ),
        ModelFile(
            filename="mmproj-gemma-4-E4B-it-Q8_0.gguf",
            url="https://huggingface.co/ggml-org/gemma-4-E4B-it-GGUF/resolve/main/mmproj-gemma-4-E4B-it-Q8_0.gguf?download=true",
            sha256="197f49a93027f9843772bd24a6a9e0be2a32a788de5a3def330e9c585d86edd1",
            byte_size=559874816,
            role="mmproj",
        ),
    ),
    tasks=("vision_describe",),
    status="experimental",
    note="Fallback rápido L12/H24: bajo coste, pero menor fidelidad estructural en la batería documental dev16.",
    hardware_profiles=("L12", "H24"),
)


QWEN35_9B_Q4 = ModelSpec(
    model_id="unsloth/Qwen3.5-9B-GGUF:Q4_K_M",
    storage_name="qwen3.5-9b-q4_k_m",
    upstream="https://huggingface.co/unsloth/Qwen3.5-9B-GGUF",
    quantization="Q4_K_M + mmproj BF16",
    files=(
        ModelFile(
            filename="Qwen3.5-9B-Q4_K_M.gguf",
            url="https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/resolve/main/Qwen3.5-9B-Q4_K_M.gguf?download=true",
            sha256="03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8",
            byte_size=None,
            role="model",
        ),
        ModelFile(
            filename="mmproj-BF16.gguf",
            url="https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/resolve/main/mmproj-BF16.gguf?download=true",
            sha256="853698ce7aa6c7ba732478bad280240969ddf7b0fcbf93900046f63903a83383",
            byte_size=None,
            role="mmproj",
        ),
    ),
    tasks=("vision_describe",),
    status="experimental",
    note="Default lógico L12 desde dev16 por fidelidad estructural; la validación en GPU física de 12 GB sigue pendiente.",
    hardware_profiles=("L12", "H24"),
)


GEMMA4_26B_A4B_Q4 = ModelSpec(
    model_id="ggml-org/gemma-4-26B-A4B-it-GGUF:Q4_0",
    storage_name="gemma-4-26b-a4b-it-q4_0",
    upstream="https://huggingface.co/ggml-org/gemma-4-26B-A4B-it-GGUF",
    quantization="Q4_0 + mmproj Q8_0",
    files=(
        ModelFile(
            filename="gemma-4-26B-A4B-it-Q4_0.gguf",
            url="https://huggingface.co/ggml-org/gemma-4-26B-A4B-it-GGUF/resolve/main/gemma-4-26B-A4B-it-Q4_0.gguf?download=true",
            sha256="d208665ab1cd3a69f7a9a4bc59430e8448c8093d9b06334f566ac59d6d504a03",
            byte_size=None,
            role="model",
        ),
        ModelFile(
            filename="mmproj-gemma-4-26B-A4B-it-Q8_0.gguf",
            url="https://huggingface.co/ggml-org/gemma-4-26B-A4B-it-GGUF/resolve/main/mmproj-gemma-4-26B-A4B-it-Q8_0.gguf?download=true",
            sha256="cc4e855736da450bf1e162d8cccfe0ad685727d0c9e04ef7dd8d884f3121039b",
            byte_size=None,
            role="mmproj",
        ),
    ),
    tasks=("vision_describe",),
    status="experimental",
    note="Default H24 desde dev16 por equilibrio entre fidelidad documental, tiempo y margen de VRAM.",
    hardware_profiles=("H24",),
)


QWEN36_35B_A3B_Q4 = ModelSpec(
    model_id="ggml-org/Qwen3.6-35B-A3B-GGUF:Q4_K_M",
    storage_name="qwen3.6-35b-a3b-q4_k_m",
    upstream="https://huggingface.co/ggml-org/Qwen3.6-35B-A3B-GGUF",
    quantization="Q4_K_M + mmproj Q8_0",
    files=(
        ModelFile(
            filename="Qwen3.6-35B-A3B-Q4_K_M.gguf",
            url="https://huggingface.co/ggml-org/Qwen3.6-35B-A3B-GGUF/resolve/main/Qwen3.6-35B-A3B-Q4_K_M.gguf?download=true",
            sha256="671e47e0ec53c665d048b98c3ecbfd5236b5ca9c3e02ed19fc8f81f7b85140c7",
            byte_size=None,
            role="model",
        ),
        ModelFile(
            filename="mmproj-Qwen3.6-35B-A3B-Q8_0.gguf",
            url="https://huggingface.co/ggml-org/Qwen3.6-35B-A3B-GGUF/resolve/main/mmproj-Qwen3.6-35B-A3B-Q8_0.gguf?download=true",
            sha256="904cbf8c8e876220066ab3bf676c7efa40f3da372276fdaf8b01d2fb2a37a51d",
            byte_size=None,
            role="mmproj",
        ),
    ),
    tasks=("vision_describe",),
    status="experimental",
    note="Referencia H24 de mayor detalle; más lenta y con mayor uso de VRAM que Gemma 26B en la batería documental dev16.",
    hardware_profiles=("H24",),
)


MODEL_CATALOG: tuple[ModelSpec, ...] = (
    MINICPM_V46,
    GEMMA4_E4B_Q4,
    QWEN35_9B_Q4,
    GEMMA4_26B_A4B_Q4,
    QWEN36_35B_A3B_Q4,
)
BOOTSTRAP_MODEL = MINICPM_V46
PROFILE_DEFAULT_MODELS: dict[str, ModelSpec] = {
    "L12": QWEN35_9B_Q4,
    "H24": GEMMA4_26B_A4B_Q4,
}


def get_model_spec(model_id: str) -> ModelSpec:
    for spec in MODEL_CATALOG:
        if spec.model_id == model_id:
            return spec
    known = ", ".join(spec.model_id for spec in MODEL_CATALOG)
    raise KeyError(f"Modelo desconocido: {model_id}. Catálogo: {known}")


def _data_base() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            return Path(local).expanduser()
        return Path.home() / "AppData" / "Local"
    xdg = os.environ.get("XDG_DATA_HOME")
    return Path(xdg).expanduser() if xdg else Path.home() / ".local" / "share"


def data_root() -> Path:
    explicit = os.environ.get("AW_AI_DATA_HOME") or os.environ.get("AW_AI01_DATA_HOME")
    if explicit:
        return Path(explicit).expanduser().resolve()
    base = _data_base().resolve()
    current = base / "archive-workbench-ai"
    legacy = base / "archive-workbench-ai01"
    if current.exists() or not legacy.exists():
        return current
    return legacy


def model_dir(spec: ModelSpec = BOOTSTRAP_MODEL) -> Path:
    return data_root() / "models" / spec.storage_name


def model_path(spec: ModelSpec = BOOTSTRAP_MODEL) -> Path:
    file = next(item for item in spec.files if item.role == "model")
    return model_dir(spec) / file.filename


def mmproj_path(spec: ModelSpec = BOOTSTRAP_MODEL) -> Path:
    file = next(item for item in spec.files if item.role == "mmproj")
    return model_dir(spec) / file.filename
