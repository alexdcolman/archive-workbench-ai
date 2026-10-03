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

El candidato Linux/NVIDIA se compila con NCCL deshabilitado (`GGML_CUDA_NCCL=OFF`) y se valida también fuera de la imagen CUDA usada para compilar. OpenMP permanece habilitado y `libgomp.so.1` se empaqueta con su aviso de licencia para que no dependa de paquetes adicionales del host. El tar no debe contener NCCL ni dependencias compartidas no resueltas distintas de `libcuda.so.1`, que pertenece al driver NVIDIA del host. `runtime inspect` y `doctor` sólo consideran disponible un runtime cuyo `--version` puede ejecutarse correctamente.

### Gate de lifecycle del bridge congelado

Las candidatas PyInstaller `--onefile` deben iniciar el daemon del bridge como una instancia independiente. `bridge start` fija `PYINSTALLER_RESET_ENVIRONMENT=1` al relanzar el mismo ejecutable congelado, porque el daemon sobrevive al proceso iniciador y no puede reutilizar su directorio temporal `_MEI`. El workflow nativo ejecuta un smoke específico que entrega un job al daemon después de que `bridge start` terminó y rechaza pérdidas de prompts/esquemas empaquetados.

## Gate dev29 — promoción de runtime publicado

La promoción del runtime Linux/NVIDIA exige tres identidades coincidentes: tar validado físicamente, SHA-256 fijado y URL inmutable pública. El asset vigente es `runtime-b10903-linux-nvidia-20261001/llama-b10903-bin-ubuntu-cuda-12.8-x64.tar.gz`, SHA-256 `b0b02cf52a910e1ec1addf58491c9896dd73c06383e0d5ba8884a852658e56bf`. Una vez cambiado el catálogo, se reconstruyen los nativos; el workflow CUDA no se repite salvo cambio material del runtime.

## Gate dev30 — lifecycle del bridge en Windows

El run multiplataforma dev29 `37147252924` cerró Linux x64 y ambos macOS, pero Windows falló en `bridge start`. La causa se aisló en `_pid_alive()`: `os.kill(pid, 0)` conserva semántica de probe en POSIX, pero en Windows los valores que no son eventos especiales de consola se tramitan mediante `TerminateProcess`. Dev30 usa un probe Win32 no destructivo (`OpenProcess` con derecho `SYNCHRONIZE` + `WaitForSingleObject(..., 0)`) y reserva `os.kill(pid, 0)` para POSIX. El workflow Windows vuelca `bridge.log` si el start nativo falla.
