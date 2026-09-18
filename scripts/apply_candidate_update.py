from __future__ import annotations

import argparse
import shutil
from pathlib import Path

SKIP_DIRS = {".git", ".venv", ".pytest_cache", ".mypy_cache", ".ruff_cache", "__pycache__", "build", "dist", "delivery"}


def should_skip(relative: Path) -> bool:
    return any(part in SKIP_DIRS or part.endswith(".egg-info") for part in relative.parts)


def apply_update(source: Path, target: Path) -> int:
    source = source.resolve()
    target = target.resolve()
    if not (source / "pyproject.toml").is_file():
        raise SystemExit(f"ERROR: fuente Archive Workbench AI inválida: {source}")
    target.mkdir(parents=True, exist_ok=True)
    copied = 0
    for path in sorted(source.rglob("*")):
        rel = path.relative_to(source)
        if should_skip(rel):
            continue
        dest = target / rel
        if path.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        copied += 1
    print(f"Fuente Archive Workbench AI: {source}")
    print(f"Destino: {target}")
    legacy_source = target / "src" / "archive_workbench_ai01"
    if (source / "src" / "archive_workbench_ai").is_dir() and legacy_source.is_dir():
        shutil.rmtree(legacy_source)
        print(f"Retirado módulo fuente legado: {legacy_source}")
    legacy_egg = target / "src" / "archive_workbench_ai01.egg-info"
    if legacy_egg.exists():
        shutil.rmtree(legacy_egg)
        print(f"Retirado metadata legado: {legacy_egg}")
    print(f"Archivos copiados: {copied}")
    print("Preservados: .git, .venv, caches, build/dist, *.egg-info y delivery/")
    return copied


def main() -> int:
    parser = argparse.ArgumentParser(description="Aplicar una candidata de Archive Workbench AI sin tocar el entorno local.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    args = parser.parse_args()
    apply_update(args.source, args.target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
