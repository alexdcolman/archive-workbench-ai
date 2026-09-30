# Distribución y plataformas

Archive Workbench AI se distribuye de forma modular. El objetivo es que una actualización del motor no obligue a redistribuir Archive Workbench, `llama.cpp` ni varios gigabytes de modelos.

## Componentes

La distribución separa cuatro piezas:

1. **Archive Workbench**: aplicación archivística y responsable de selección, autorización, persistencia y revisión.
2. **Archive Workbench AI**: aplicación nativa administrada; el paquete Python/CLI queda como superficie técnica.
3. **Runtime**: una revisión fijada de `llama.cpp` con `llama-server`.
4. **Modelos**: pesos multimodales descargados por separado.

EXP-01 y el handoff versionado son la frontera contractual. Archive Workbench AI no abre la SQLite de Archive Workbench.

## Matriz del runtime fijado

| Sistema | Arquitectura | Variante | Ruta de instalación |
| --- | --- | --- | --- |
| Linux | x86_64 | CPU | binario upstream verificado |
| Linux | arm64 | CPU | binario upstream verificado |
| Linux | x86_64 | NVIDIA | runtime administrado CUDA 12.8 precompilado y SHA-256 fijado |
| Linux | arm64 | NVIDIA | no declarado para el primer release administrado |
| Windows | x64 | CPU | binario upstream verificado |
| Windows | ARM64 | CPU | binario upstream verificado |
| Windows | x64 | NVIDIA | binario CUDA 12.4 + runtime CUDA verificados |
| macOS | Apple Silicon | Metal | binario upstream verificado |
| macOS | Intel | Metal | binario upstream verificado |

La revisión fijada es `llama.cpp b10903`, commit `481c65f091f74c5e7089dd0a3a1cc6b50cced31e`.

El runtime NVIDIA Linux x86_64 se construyó en GitHub Actions sin GPU del runner, pasó las validaciones de dependencias dinámicas y se identificó con SHA-256 `d41bb204eb09995bfe387950435ddd84635aaaed28fade425d7d35c1bb2cee89`. Para mantener el código privado durante los gates manuales, los binarios candidatos se publican separadamente en `alexdcolman/archive-workbench-ai-dist`.

Esta matriz describe **rutas de instalación disponibles**, no una afirmación de que todos los perfiles/modelos hayan sido validados físicamente en cada combinación. El cierre H24 previo se realizó sobre Linux/NVIDIA RTX 3090. L12 mantiene pendiente su gate específico en hardware físico de 12 GB.

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

Actualizar la aplicación nativa no debe borrar runtime ni modelos. Cambiar o reparar el runtime requiere una acción explícita. Cambiar de modelo requiere una descarga explícita. El paquete Python permanece como superficie técnica.

Antes de promover una nueva revisión de `llama.cpp`, deben repetirse los gates de runtime pertinentes. Antes de cambiar el modelo por defecto de un perfil, debe existir evidencia comparable que justifique el cambio.

## Integración administrada con Archive Workbench

Archive Workbench se distribuye actualmente mediante imágenes Docker CPU/GPU. Archive Workbench AI, en cambio, necesita ejecutarse como proceso nativo para aprovechar adecuadamente las aceleraciones del host, en particular Metal en macOS y las toolchains NVIDIA propias de cada sistema.

Por ello, Archive Workbench AI no se copia dentro del contenedor de Archive Workbench. La integración administrada usa un **compañero local del host** y un buzón global por usuario administrado por Archive Workbench AI y montado de forma acotada dentro del contenedor. El contenedor sólo intercambia EXP-01, parámetros acotados, `result.zip` y handoff mediante esa carpeta compartida. No hay puerto de red, rutas arbitrarias ni acceso a SQLite.

Los launchers administrados de Archive Workbench deben descubrir la instalación canónica de Archive Workbench AI e iniciar el compañero sin configuración manual. `PATH` y `ARCHIVE_WORKBENCH_AI_EXECUTABLE` quedan como overrides técnicos. La integración sigue en estado pre-release hasta validar esos launchers con las imágenes definitivas de Windows CPU, Ubuntu CPU y Ubuntu GPU NVIDIA, y completar la matriz adicional que se declare soportada.

## Construcción de artefactos nativos

Las candidatas nativas se construyen en GitHub Actions sobre runners de la plataforma correspondiente. El workflow produce un `.deb` para Ubuntu x64, un instalador por usuario para Windows x64 y DMG para macOS Intel/Apple Silicon. Cada job ejecuta smoke del binario congelado (`--version`, estado de Setup y ciclo `bridge start/status/stop`) antes de publicar el artefacto de Actions.

El runtime NVIDIA de Linux se construye en un workflow separado dentro de una imagen de desarrollo CUDA, a partir del commit fijado de `llama.cpp`. La construcción no usa la GPU ni la toolchain de la computadora usuaria. El runtime CUDA 12.8 x64 que cerró este gate se reutiliza sin recompilar; sólo los instaladores nativos deben reconstruirse después de incorporar su URL+SHA al catálogo.

## Repositorio público de binarios candidatos

Durante la validación previa al release público, el código fuente de Archive Workbench AI puede permanecer privado. Los artefactos que necesita el recorrido cero-terminal se publican en `alexdcolman/archive-workbench-ai-dist`, release candidato publicado `v0.1.0.dev24`; las candidatas nativas posteriores pueden reutilizar ese runtime fijado sin recompilarlo.

Ese repositorio contiene únicamente binarios/instaladores y checksums. No reemplaza el repositorio fuente ni altera el versionado del protocolo. La validación manual debe descargar exactamente esos assets.
