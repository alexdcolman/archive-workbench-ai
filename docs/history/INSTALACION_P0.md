# Instalación P0

> **Documento histórico.** Conserva el estado y la evidencia de una fase previa de desarrollo. No contiene las instrucciones vigentes de instalación ni el estado actual del release. Para uso actual, consulte `../INSTALACION.md`, `../DISTRIBUCION.md` y el `README.md` del repositorio.

P0 requiere sólo Python 3.11 o superior. No requiere CUDA, `llama.cpp`, GPU ni acceso a red.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
aw-ai doctor --json
```

`models pull` está deshabilitado deliberadamente en P0 y devuelve código 5. La instalación de runtime/modelos se incorpora en P1.
