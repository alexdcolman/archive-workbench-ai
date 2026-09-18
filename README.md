# Archive Workbench AI

Archive Workbench AI es el motor local de análisis asistido de [Archive Workbench](https://github.com/alexdcolman/archive-workbench). Se ejecuta como un componente separado: recibe un paquete de exportación de Archive Workbench, procesa sus imágenes con un modelo multimodal local y devuelve propuestas que Archive Workbench presenta para revisión humana.

El motor **no abre la base SQLite de Archive Workbench, no aplica cambios por sí mismo y no convierte una salida automática en una decisión archivística**. La selección del material, la autorización del análisis, la revisión, la aceptación y la vigencia pertenecen a Archive Workbench.

> **Estado actual:** pre-release. La integración técnica nativa AW ↔ Archive Workbench AI y el puente local para la distribución administrada basada en Docker están implementados. Falta validarlos sobre las imágenes definitivas y los artefactos de distribución publicados en las plataformas declaradas antes del primer release público estable.

## Qué hace

El flujo normal es:

1. Archive Workbench selecciona y autoriza el material.
2. Archive Workbench genera un paquete EXP-01 con imágenes y contexto documental.
3. Archive Workbench AI ejecuta la inferencia local.
4. El motor devuelve un resultado consolidado y un paquete de propuestas.
5. Archive Workbench permite inspeccionar e incorporar esas propuestas a su capa de revisión.
6. Una persona decide qué aceptar, corregir o descartar.

Para un EXP-01 completo, `aw-ai analyze` administra internamente el procesamiento por lotes y devuelve un único resultado consolidado. No es necesario dividir manualmente las páginas.

## Privacidad y red

La inferencia se realiza localmente mediante `llama.cpp`. Una vez instalados el runtime y los modelos, `analyze`, `run` y los benchmarks no necesitan acceso a Internet.

La red se usa únicamente cuando una persona solicita una descarga, por ejemplo:

- `aw-ai runtime install`, para obtener el runtime fijado cuando existe un binario apropiado para la plataforma;
- `aw-ai models pull`, para descargar un modelo del catálogo.

Los modelos no se incluyen dentro del repositorio ni del paquete de Archive Workbench AI.

## Requisitos

La distribución administrada pública no requerirá Python instalado por la persona usuaria. Python 3.11 o posterior sólo es requisito para instalación desde fuente y desarrollo.

- Espacio suficiente para el runtime y los modelos elegidos.
- Para aceleración NVIDIA en Linux: controlador NVIDIA compatible. La distribución administrada no compila CUDA, Git ni CMake en la computadora usuaria.
- Para aceleración NVIDIA en Windows: una GPU y controlador compatibles con la variante CUDA publicada por `llama.cpp`.
- En macOS, el runtime nativo utiliza Metal cuando la plataforma lo permite.

La ruta de instalación existe para Linux, Windows y macOS. La validación de calidad y rendimiento cerrada del perfil H24 se realizó sobre Linux con NVIDIA RTX 3090. El perfil L12 tiene selección lógica cerrada, pero la validación física específica sobre una GPU de 12 GB continúa pendiente.

## Instalación

Archive Workbench AI Setup ya está implementado como interfaz local sin terminal. Los instaladores nativos siguen en preparación y deben superar sus smokes de empaquetado antes del primer release público. Mientras el proyecto siga en pre-release, la instalación desde fuente siguiente es exclusivamente para desarrollo y diagnóstico:

```bash
git clone https://github.com/alexdcolman/archive-workbench-ai.git
cd archive-workbench-ai
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
```

En Windows PowerShell, la activación equivalente es:

```powershell
.\.venv\Scripts\Activate.ps1
```

Después puede prepararse el runtime local:

```bash
aw-ai runtime install --variant auto
aw-ai runtime inspect --json
```

Y descargar el modelo correspondiente al perfil que se vaya a utilizar. Los defaults actuales son:

- H24: Gemma 4 26B-A4B Q4_0.
- L12: Qwen3.5 9B Q4_K_M.

Por ejemplo:

```bash
aw-ai models pull 'ggml-org/gemma-4-26B-A4B-it-GGUF:Q4_0'
aw-ai doctor --json
```

La guía completa por plataforma está en [`docs/INSTALACION.md`](docs/INSTALACION.md).

### Archive Workbench AI Setup

La distribución administrada abre **Archive Workbench AI Setup** como una interfaz local en el navegador, escuchando sólo en `127.0.0.1`. Desde allí se consulta el estado del runtime, los modelos y el compañero local, y se inicia explícitamente la preparación de L12/H24 o una reparación. Abrir el Setup no descarga ni modifica nada por sí mismo.

En Linux/NVIDIA, el Setup administrado bloquea cualquier compilación desde fuente: hasta que el runtime CUDA precompilado y verificado quede publicado en el catálogo, esa preparación se informa como pendiente en lugar de exigir una toolchain local.

## Uso con Archive Workbench

En la distribución administrada, Archive Workbench descubre Archive Workbench AI en su ubicación de instalación canónica e inicia el compañero local automáticamente. `PATH` y la variable siguiente se conservan únicamente como overrides para desarrollo/diagnóstico:

```bash
export ARCHIVE_WORKBENCH_AI_EXECUTABLE=/ruta/a/aw-ai
```

El recorrido visible se realiza desde **Análisis asistido** en Archive Workbench. La persona elige qué analizar y pulsa **Iniciar análisis**; la salida vuelve como propuesta para revisión.

La frontera entre ambos proyectos permanece en EXP-01 y el handoff versionado. Archive Workbench AI no importa módulos privados de Archive Workbench ni escribe en su SQLite.

En la distribución administrada con Docker, Archive Workbench monta únicamente el buzón global por usuario administrado por Archive Workbench AI. El contenedor deposita allí únicamente el EXP-01 autorizado y parámetros acotados; el compañero nativo procesa el trabajo y devuelve `result.zip` + `handoff.zip`. No se abre ningún puerto ni se expone SQLite. Véase [`docs/INTEGRACION_ARCHIVE_WORKBENCH.md`](docs/INTEGRACION_ARCHIVE_WORKBENCH.md).

## Perfiles y modelos

Los perfiles describen una configuración lógica de hardware y un modelo por defecto. No representan una garantía universal sobre cualquier equipo.

| Perfil | Modelo por defecto | Estado |
| --- | --- | --- |
| H24 | Gemma 4 26B-A4B Q4_0 | Validado en RTX 3090 de 24 GB |
| L12 | Qwen3.5 9B Q4_K_M | Selección lógica cerrada; prueba física de 12 GB pendiente |

MiniCPM-V 4.6 permanece como baseline técnico y existen modelos alternativos en el catálogo para comparación y diagnóstico. La justificación de la selección y las limitaciones se documentan en [`docs/MODELOS_Y_HARDWARE.md`](docs/MODELOS_Y_HARDWARE.md).

## Interfaz de línea de comandos

Comandos principales:

```bash
aw-ai --version
aw-ai doctor --json
aw-ai capabilities --json
aw-ai runtime install --variant auto
aw-ai runtime inspect --json
aw-ai models list --json
aw-ai models pull MODEL_ID
aw-ai analyze --input EXP01.zip --profile H24
```

`aw-ai run`, `benchmark` y `handoff` permanecen disponibles para reproducción técnica, pruebas y diagnóstico. El uso cotidiano desde Archive Workbench no requiere operar esos comandos manualmente.

## Contratos y trazabilidad

Los contratos públicos actuales son:

- protocolo de bajo nivel: `archive-workbench-ai/0.1`;
- tarea: `vision_describe/0.1`;
- handoff de propuestas: `archive_workbench_ai_result_handoff/0.1`.

El protocolo de bajo nivel admite hasta tres targets por request. `aw-ai analyze` conserva ese límite sólo como detalle interno y entrega un único resultado consolidado para un EXP-01 completo.

La referencia está en [`docs/PROTOCOLO_0_1.md`](docs/PROTOCOLO_0_1.md).

## Documentación

- [Instalación](docs/INSTALACION.md)
- [Distribución y plataformas](docs/DISTRIBUCION.md)
- [Integración con Archive Workbench](docs/INTEGRACION_ARCHIVE_WORKBENCH.md)
- [Modelos y hardware](docs/MODELOS_Y_HARDWARE.md)
- [Protocolo 0.1](docs/PROTOCOLO_0_1.md)
- [Desarrollo y pruebas](docs/DESARROLLO.md)
- [Preparación de releases](docs/RELEASE.md)
- [Historial técnico](docs/history/)

## Desarrollo y pruebas

La suite canónica usa el mismo intérprete en el que está instalado el paquete:

```bash
VENV_PY="$PWD/.venv/bin/python"
"$VENV_PY" -m unittest discover -s tests -v
```

No se debe sustituir ese gate por un `pytest` global que pueda resolver a otro intérprete.

## Licencia y cita

Archive Workbench AI se distribuye bajo GNU Affero General Public License v3.0 o posterior (`AGPL-3.0-or-later`).

Desarrollo: Alex Colman, en el marco del Grupo de Investigación en Archivos de la Represión (GIAR).

[`CITATION.cff`](CITATION.cff) contiene los metadatos de cita. Los runtimes, modelos y dependencias de terceros conservan sus propias licencias; véase [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
