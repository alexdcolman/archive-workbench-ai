#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${AW_AI_RUNTIME_HOME:-}" ]]; then
  ROOT="$AW_AI_RUNTIME_HOME"
elif [[ -n "${AW_AI01_RUNTIME_HOME:-}" ]]; then
  ROOT="$AW_AI01_RUNTIME_HOME"
elif [[ -d "$HOME/.local/share/archive-workbench-ai01/runtime/llama.cpp-b10903" && ! -d "$HOME/.local/share/archive-workbench-ai/runtime/llama.cpp-b10903" ]]; then
  ROOT="$HOME/.local/share/archive-workbench-ai01/runtime/llama.cpp-b10903"
else
  ROOT="$HOME/.local/share/archive-workbench-ai/runtime/llama.cpp-b10903"
fi
SRC="$ROOT/src"
BUILD="$ROOT/build"
EXPECTED_COMMIT="481c65f"

mkdir -p "$ROOT"
if [[ ! -d "$SRC/.git" ]]; then
  git clone --depth 1 --branch b10903 https://github.com/ggml-org/llama.cpp.git "$SRC"
fi

cd "$SRC"
git fetch --depth 1 origin tag b10903
git checkout --detach b10903
ACTUAL="$(git rev-parse HEAD)"
if [[ "$ACTUAL" != "$EXPECTED_COMMIT"* ]]; then
  echo "ERROR: b10903 no coincide con el commit esperado: $ACTUAL" >&2
  exit 2
fi

cmake -S "$SRC" -B "$BUILD" \
  -DGGML_CUDA=ON \
  -DGGML_CUDA_FA_QUANTS='q4_0-q4_0;q8_0-q8_0;f16-f16;bf16-bf16'
cmake --build "$BUILD" --config Release --target llama-server -j "$(nproc)"

BIN="$BUILD/bin/llama-server"
"$BIN" --version || true
printf '\nRuntime listo. Para usarlo con el plugin:\nexport AW_AI_LLAMA_SERVER=%q\n' "$BIN"
