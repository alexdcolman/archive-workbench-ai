# Instalación P1

P1 mantiene tres capas independientes: plugin, runtime y modelo. Archive Workbench no se modifica.

## 1. Plugin

Crear una venv propia e instalar el wheel de Archive Workbench AI.

## 2. Runtime llama.cpp

P1 se probó conceptualmente contra `llama.cpp` build `b10903`, commit `481c65f`. En Linux/NVIDIA puede compilarse con:

```bash
bash scripts/build_llama_cpp_b10903_cuda.sh
export AW_AI_LLAMA_SERVER="$HOME/.local/share/archive-workbench-ai/runtime/llama.cpp-b10903/build/bin/llama-server"
aw-ai runtime inspect --json
```

El script no forma parte de Archive Workbench y compila el runtime en el espacio de usuario.

## 3. Modelo bootstrap

```bash
aw-ai models pull 'ggml-org/MiniCPM-V-4.6-GGUF:Q4_K_M'
aw-ai models inspect 'ggml-org/MiniCPM-V-4.6-GGUF:Q4_K_M' --verify --json
```

La descarga es explícita y verifica SHA-256 de ambos archivos. `run` no descarga nada.

## 4. Diagnóstico

```bash
aw-ai doctor --json
```

`status=ok` significa que runtime y modelo reales están disponibles. `setup_required` indica que todavía falta una de esas capas.

## 5. Ejecución

```bash
aw-ai run \
  --request request.json \
  --input exp01.zip \
  --output result.zip \
  --backend llama_cpp
```

La inferencia real usa sólo `127.0.0.1`; no permite fallback de red durante `run`.


## Diagnósticos

Los fallos de inferencia generan automáticamente un ZIP listo para compartir en `~/Downloads/AWAI_DIAGNOSTICO_*.zip`. No hace falta buscar ni comprimir logs manualmente.
