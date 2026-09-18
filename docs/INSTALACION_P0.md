# Instalación P0

P0 requiere sólo Python 3.11 o superior. No requiere CUDA, `llama.cpp`, GPU ni acceso a red.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
aw-ai doctor --json
```

`models pull` está deshabilitado deliberadamente en P0 y devuelve código 5. La instalación de runtime/modelos se incorpora en P1.
