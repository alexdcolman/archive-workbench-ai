# Distribución y plataformas

Archive Workbench AI se distribuye de forma modular. El objetivo es que una actualización del motor no obligue a redistribuir Archive Workbench, `llama.cpp` ni varios gigabytes de modelos.

## Componentes

La distribución separa cuatro piezas:

1. **Archive Workbench**: aplicación archivística y responsable de selección, autorización, persistencia y revisión.
2. **Archive Workbench AI**: paquete Python y CLI `aw-ai`.
3. **Runtime**: una revisión fijada de `llama.cpp` con `llama-server`.
4. **Modelos**: pesos multimodales descargados por separado.

EXP-01 y el handoff versionado son la frontera contractual. Archive Workbench AI no abre la SQLite de Archive Workbench.

## Matriz del runtime fijado

| Sistema | Arquitectura | Variante | Ruta de instalación |
| --- | --- | --- | --- |
| Linux | x86_64 | CPU | binario upstream verificado |
| Linux | arm64 | CPU | binario upstream verificado |
| Linux | x86_64 / arm64 | NVIDIA | compilación de fuente fijada |
| Windows | x64 | CPU | binario upstream verificado |
| Windows | ARM64 | CPU | binario upstream verificado |
| Windows | x64 | NVIDIA | binario CUDA 12.4 + runtime CUDA verificados |
| macOS | Apple Silicon | Metal | binario upstream verificado |
| macOS | Intel | Metal | binario upstream verificado |

La revisión fijada es `llama.cpp b10903`, commit `481c65f091f74c5e7089dd0a3a1cc6b50cced31e`.

Esta matriz describe **rutas de instalación disponibles**, no una afirmación de que todos los perfiles/modelos hayan sido validados físicamente en cada combinación. El cierre H24 se realizó sobre Linux/NVIDIA RTX 3090. L12 mantiene pendiente su gate específico en hardware físico de 12 GB.

## Directorios de datos

Runtime y modelos se guardan fuera del repositorio y fuera de la venv:

- Linux: `${XDG_DATA_HOME:-~/.local/share}/archive-workbench-ai/`;
- macOS: `~/Library/Application Support/archive-workbench-ai/`;
- Windows: `%LOCALAPPDATA%\archive-workbench-ai\`.

Esto permite actualizar código sin borrar runtime ni pesos. `AW_AI_DATA_HOME` permite elegir otro directorio.

## Integridad

Los artefactos de runtime descargados por el instalador tienen SHA-256 fijado en el catálogo. Si el contenido recibido no coincide, no se instala. Los modelos también se verifican mediante los hashes conocidos por el catálogo.

Un release de Archive Workbench AI no debe incorporar los pesos de los modelos. Cada modelo conserva además sus propias condiciones de uso.

## Versionado

Los números de versión se separan deliberadamente:

- Archive Workbench tiene su propia versión de aplicación;
- Archive Workbench AI tiene su propia versión de paquete;
- el protocolo `archive-workbench-ai/0.1` se versiona de manera independiente;
- el handoff `archive_workbench_ai_result_handoff/0.1` se versiona de manera independiente;
- `llama.cpp` conserva su tag/commit fijado;
- los modelos se identifican por catálogo y hashes.

Una nueva versión de cualquiera de estos componentes no obliga por sí sola a incrementar todos los demás. La compatibilidad debe declararse mediante capacidades y contratos, no por igualdad de números de versión.

## Actualizaciones

Actualizar el paquete Python no debe borrar runtime ni modelos. Cambiar el runtime requiere una acción explícita. Cambiar de modelo requiere una descarga explícita.

Antes de promover una nueva revisión de `llama.cpp`, deben repetirse los gates de runtime pertinentes. Antes de cambiar el modelo por defecto de un perfil, debe existir evidencia comparable que justifique el cambio.

## Integración administrada con Archive Workbench

Archive Workbench se distribuye actualmente mediante imágenes Docker CPU/GPU. Archive Workbench AI, en cambio, necesita ejecutarse como proceso nativo para aprovechar adecuadamente las aceleraciones del host, en particular Metal en macOS y las toolchains NVIDIA propias de cada sistema.

Por ello, Archive Workbench AI no se copia dentro del contenedor de Archive Workbench. La integración administrada usa un **compañero local del host** y un buzón de trabajos dentro de `ArchiveWorkbenchData/Settings/archive-workbench-ai-bridge`. El contenedor sólo intercambia EXP-01, parámetros acotados, `result.zip` y handoff mediante esa carpeta compartida. No hay puerto de red, rutas arbitrarias ni acceso a SQLite.

Los launchers administrados de Archive Workbench pueden iniciar el compañero cuando encuentran `aw-ai` (o cuando se define `ARCHIVE_WORKBENCH_AI_EXECUTABLE`). La integración sigue en estado pre-release hasta validar esos launchers con las imágenes definitivas de Windows CPU, Ubuntu CPU y Ubuntu GPU NVIDIA, y completar la matriz adicional que se declare soportada.
