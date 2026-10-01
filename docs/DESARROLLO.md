# Desarrollo y pruebas

## Entorno

```bash
git clone https://github.com/alexdcolman/archive-workbench-ai.git
cd archive-workbench-ai
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
```

## Suite canónica

Usar el intérprete de la venv de manera explícita:

```bash
VENV_PY="$PWD/.venv/bin/python"
"$VENV_PY" -m unittest discover -s tests -v
```

Esto evita que un `pytest` instalado globalmente seleccione otro Python y produzca falsos fallos de importación.

## Contratos que no deben romperse silenciosamente

- protocolo: `archive-workbench-ai/0.1`;
- tarea: `vision_describe/0.1`;
- handoff: `archive_workbench_ai_result_handoff/0.1`;
- Archive Workbench AI no abre SQLite de Archive Workbench;
- las salidas automáticas son propuestas y requieren revisión humana;
- `analyze` puede procesar más de tres páginas, pero mantiene requests internos de hasta tres targets para el protocolo 0.1.

## Runtime

La revisión fijada se declara en `runtime_catalog.py`. Un cambio de tag/commit debe actualizar de manera coherente catálogo, hashes, documentación y pruebas. No se deben reemplazar hashes por valores obtenidos de una descarga no verificada.

El instalador de runtime nunca debe ejecutar una inferencia de forma implícita. Descargar/preparar el runtime y descargar modelos son operaciones separadas de `analyze`.

## Datos locales

Runtime y modelos viven fuera del repositorio. Las pruebas no deben depender de los pesos reales ni modificarlos. Los backends simulados permiten probar protocolo, consolidación y handoff sin GPU.

## Evidencia histórica

`docs/history/` conserva documentación de las fases y benchmarks previos. No representa instrucciones actuales de instalación y no debe usarse como fuente para el flujo público vigente.

## Smoke de ejecutable nativo

Toda candidata nativa debe ejecutar `analyze --backend mock` sobre el binario congelado de PyInstaller y verificar que se produzcan `result.zip` y `handoff.zip`. Este gate complementa `--version`, Setup y bridge, y detecta recursos o imports dinámicos ausentes del ejecutable.


## Gate del runtime NVIDIA Linux

El candidato Linux/NVIDIA se compila con NCCL deshabilitado (`GGML_CUDA_NCCL=OFF`) y se valida también fuera de la imagen CUDA usada para compilar. El tar no debe contener NCCL ni dependencias compartidas no resueltas distintas de `libcuda.so.1`, que pertenece al driver NVIDIA del host. `runtime inspect` y `doctor` sólo consideran disponible un runtime cuyo `--version` puede ejecutarse correctamente.
