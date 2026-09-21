from __future__ import annotations

from dataclasses import dataclass

PINNED_LLAMA_BUILD = 10903
PINNED_LLAMA_TAG = "b10903"
PINNED_LLAMA_COMMIT = "481c65f091f74c5e7089dd0a3a1cc6b50cced31e"

DIST_REPOSITORY = "alexdcolman/archive-workbench-ai-dist"
DIST_RELEASE_TAG = "v0.1.0.dev24"
_DIST_BASE = f"https://github.com/{DIST_REPOSITORY}/releases/download/{DIST_RELEASE_TAG}"


@dataclass(frozen=True, slots=True)
class RuntimeAsset:
    filename: str
    url: str
    sha256: str


@dataclass(frozen=True, slots=True)
class RuntimePackage:
    system: str
    machine: str
    variant: str
    assets: tuple[RuntimeAsset, ...] = ()
    source: str = "upstream-release"
    source_build: bool = False


_BASE = f"https://github.com/ggml-org/llama.cpp/releases/download/{PINNED_LLAMA_TAG}"


def _asset(filename: str, sha256: str) -> RuntimeAsset:
    return RuntimeAsset(filename=filename, url=f"{_BASE}/{filename}", sha256=sha256)


def _managed_asset(filename: str, sha256: str) -> RuntimeAsset:
    return RuntimeAsset(filename=filename, url=f"{_DIST_BASE}/{filename}", sha256=sha256)


RUNTIME_PACKAGES: tuple[RuntimePackage, ...] = (
    RuntimePackage(
        "linux",
        "x86_64",
        "cpu",
        (_asset("llama-b10903-bin-ubuntu-x64.tar.gz", "5366d9db6a3d22a8dfde0b5105d9f002438d309971594ffcb65b180d7cc3f592"),),
    ),
    RuntimePackage(
        "linux",
        "aarch64",
        "cpu",
        (_asset("llama-b10903-bin-ubuntu-arm64.tar.gz", "dfa3e27e204c5322c29419baf4b57df4aa4a30d49d9d55cbf19863e6697fdcb5"),),
    ),
    RuntimePackage(
        "linux",
        "x86_64",
        "nvidia",
        (_managed_asset("llama-b10903-bin-ubuntu-cuda-12.8-x64.tar.gz", "d41bb204eb09995bfe387950435ddd84635aaaed28fade425d7d35c1bb2cee89"),),
        source="archive-workbench-ai-dist",
    ),
    RuntimePackage("linux", "aarch64", "nvidia", source_build=True),
    RuntimePackage(
        "darwin",
        "arm64",
        "metal",
        (_asset("llama-b10903-bin-macos-arm64.tar.gz", "a1893edd4e63645fb04ac9ef89fa932d3cc7ac5c513e8002b6031dbe7d104c2d"),),
    ),
    RuntimePackage(
        "darwin",
        "x86_64",
        "metal",
        (_asset("llama-b10903-bin-macos-x64.tar.gz", "58d5f475960ce6d6c28541da0ccdbdff88bfd31b64a9db8babc0dd3add3a45f8"),),
    ),
    RuntimePackage(
        "windows",
        "x86_64",
        "cpu",
        (_asset("llama-b10903-bin-win-cpu-x64.zip", "b009259d362662f4d73633773080e0ce5d748b8556290b7973fc7249b3b83806"),),
    ),
    RuntimePackage(
        "windows",
        "arm64",
        "cpu",
        (_asset("llama-b10903-bin-win-cpu-arm64.zip", "4a9a371eb789d05699b088305c564bc81e2936287bcf2b8899cbee025349d1b4"),),
    ),
    RuntimePackage(
        "windows",
        "x86_64",
        "nvidia",
        (
            _asset("llama-b10903-bin-win-cuda-12.4-x64.zip", "1b5f44800c737485f85506651ba7f4887d6a6997ee81106f63387f29a476ea70"),
            _asset("cudart-llama-bin-win-cuda-12.4-x64.zip", "8c79a9b226de4b3cacfd1f83d24f962d0773be79f1e7b75c6af4ded7e32ae1d6"),
        ),
    ),
)


def runtime_package(system: str, machine: str, variant: str) -> RuntimePackage | None:
    for package in RUNTIME_PACKAGES:
        if (package.system, package.machine, package.variant) == (system, machine, variant):
            return package
    return None
