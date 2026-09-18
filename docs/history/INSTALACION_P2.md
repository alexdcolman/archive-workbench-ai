# Instalación y benchmark P2

> **Documento histórico.** Conserva el estado y la evidencia de una fase previa de desarrollo. No contiene las instrucciones vigentes de instalación ni el estado actual del release. Para uso actual, consulte `../INSTALACION.md`, `../DISTRIBUCION.md` y el `README.md` del repositorio.

P2 conserva la venv y el runtime `llama.cpp b10903 / 481c65f` de P1. No instala nada dentro del repositorio de Archive Workbench.

## Actualización del plugin

La ruta canónica para actualizar una candidata local es instalar el **wheel preconstruido entregado con el ZIP**. Esto evita depender de `setuptools` o de acceso a red dentro de la `.venv`. El árbol fuente puede actualizarse por separado mediante `scripts/apply_candidate_update.py`; la carpeta local puede no ser todavía un repositorio Git.

```bash
cd /home/alex/projects/archive-workbench-ai
source .venv/bin/activate
python -m pip install --upgrade --force-reinstall --no-deps /ruta/al/archive_workbench_ai-0.1.0.dev20-py3-none-any.whl
export AW_AI_LLAMA_SERVER="$HOME/.local/share/archive-workbench-ai/runtime/llama.cpp-b10903/build/bin/llama-server"
aw-ai --version
aw-ai doctor --json
```

No usar `pip install -e . --no-build-isolation` como instrucción de actualización si la venv no contiene el backend de build requerido.

Dev14 incorpora `Pillow>=10` únicamente en la venv de Archive Workbench AI para preparar páginas locales como PNG reproducibles. No modifica el entorno de Archive Workbench.

## Estado L12

Gemma 4 E4B-it Q4_0 es el candidato principal provisional. MiniCPM es baseline y Qwen3.5-9B no lo desplaza. Falta validación efectiva/física de 12 GB.

## Estado H24 sintético

Gemma 26B-A4B y Qwen3.6-35B-A3B completaron 3/3. Qwen3.6 alcanzó 19.624 MiB de VRAM y completó con `--fit`, por lo que no hace falta abrir CPU-MoE en este punto. No repetir el corpus sintético salvo regresión concreta.

Consultar `BENCHMARK_P1_P2_20260915.md` para métricas y evaluación cualitativa.

## Preparar el corpus ampliado

Dev14 admite entre una y tres imágenes por job. TIFF de una sola página, PNG, JPEG y otros formatos abiertos por Pillow se normalizan a PNG sin redimensionar.

```bash
aw-ai benchmark prepare \
  --profile H24 \
  --images \
    /ruta/a/pagina_1.tiff \
    /ruta/a/pagina_2.tiff \
    /ruta/a/pagina_3.tiff
```

Salida por defecto:

```text
~/Downloads/AWAI_BENCHMARK_JOB_<timestamp>.zip
```

El job contiene `job_manifest.json`, `request.json` y `exp01.zip`. El manifest conserva hashes, tamaños, formato y dimensiones de las fuentes, pero no rutas absolutas locales.

Si una imagen tiene más de una página/cuadro, el comando falla explícitamente; no selecciona una página de manera silenciosa.

## Benchmark ampliado H24

La nueva batería debe ejecutar **el mismo job** con los tres candidatos relevantes:

```bash
aw-ai benchmark run \
  --job "$HOME/Downloads/AWAI_BENCHMARK_JOB_<timestamp>.zip" \
  --models \
    'ggml-org/gemma-4-E4B-it-GGUF:Q4_0' \
    'ggml-org/gemma-4-26B-A4B-it-GGUF:Q4_0' \
    'ggml-org/Qwen3.6-35B-A3B-GGUF:Q4_K_M'
```

Esto genera un único `~/Downloads/AWAI_BENCHMARK_<timestamp>.zip`. Repetir E4B/26B/Qwen3.6 aquí está justificado porque cambia el corpus; no reabre la batería sintética previa.

## Compatibilidad con jobs anteriores

La interfaz anterior sigue vigente:

```bash
aw-ai benchmark run \
  --request p2_benchmark/request_H24.json \
  --input p2_benchmark/exp01.zip \
  --models 'ggml-org/gemma-4-E4B-it-GGUF:Q4_0'
```

`--job` y el par `--request/--input` son alternativas excluyentes.


## EXP-01 1.1 desde Archive Workbench 1.2.0

Desde dev16 no hace falta transformar la exportación de AW: `aw-ai run` y `benchmark run` aceptan directamente EXP-01 schema 1.1. El paquete debe incluir contexto (`context/objects.jsonl`) para que el prompt reciba texto canónico + bbox. EXP-01 1.0 permanece admitido para evidencia histórica y jobs preparados desde imágenes, pero no es el formato preferido para cerrar la selección de modelos.

## Ejecución completa desde dev20

Para analizar un EXP-01 real completo y obtener directamente un único handoff para Archive Workbench:

```bash
cd /home/alex/projects/archive-workbench-ai
source .venv/bin/activate
export AW_AI_LLAMA_SERVER="$HOME/.local/share/archive-workbench-ai/runtime/llama.cpp-b10903/build/bin/llama-server"

aw-ai analyze \
  --input /ruta/al/exp01.zip \
  --profile H24
```

El comando selecciona todas las páginas del EXP-01 por defecto, usa el modelo default del perfil y crea un único result bundle y un único handoff. Internamente conserva requests 0.1 de hasta tres targets para compatibilidad/trazabilidad; ese batching ya no forma parte del flujo manual.

## Actualización local dev20: intérprete canónico

En el árbol local conocido de Archive Workbench AI no se debe usar `pytest` desnudo como gate de actualización. Se observó que, aun después de `source .venv/bin/activate`, ese comando podía resolver al `pytest` del sistema y ejecutar `/usr/bin/python3`, dejando fuera de `sys.path` el paquete instalado en la venv.

Usar siempre el intérprete de forma explícita:

```bash
VENV_PY="$HOME/projects/archive-workbench-ai/.venv/bin/python"
"$VENV_PY" -m pip install --upgrade --force-reinstall --no-deps /ruta/al/archive_workbench_ai-0.1.0.dev20-py3-none-any.whl
"$VENV_PY" -m archive_workbench_ai.cli --version
"$VENV_PY" -m unittest discover -s tests -p 'test_handoff.py' -v
"$VENV_PY" -m unittest discover -s tests -p 'test_protocol.py' -v
"$VENV_PY" -m unittest discover -s tests -p 'test_complete_analysis.py' -v
```

Esto evita depender de la resolución de `PATH` y garantiza que los subprocess de las pruebas hereden el mismo `sys.executable` donde está instalado Archive Workbench AI.


### Compatibilidad con la instalación local anterior

Dev20 puede ejecutarse sin mover inmediatamente `/home/alex/projects/archive-workbench-ai`, porque una venv existente contiene rutas absolutas. El código nuevo reconoce `AW_AI_LLAMA_SERVER` y, como compatibilidad, `AW_AI01_LLAMA_SERVER`; también reutiliza `~/.local/share/archive-workbench-ai01/` cuando todavía no existe el nuevo `~/.local/share/archive-workbench-ai/`. El cambio de ruta del repositorio se hará al crear el repositorio Git canónico y una venv nueva.
