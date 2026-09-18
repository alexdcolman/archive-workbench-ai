# Instalación

Archive Workbench AI se instala como un componente separado de Archive Workbench. El paquete Python, el runtime `llama.cpp` y los modelos tienen ciclos de instalación y actualización independientes.

## 1. Instalar Archive Workbench AI

Requiere Python 3.11 o posterior. En un release público, la ruta preferida será instalar el wheel publicado con ese release. Para una instalación desde el repositorio:

```bash
git clone https://github.com/alexdcolman/archive-workbench-ai.git
cd archive-workbench-ai
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
```

En Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
```

Comprobar:

```bash
aw-ai --version
aw-ai capabilities --json
```

## 2. Instalar el runtime local

El comando recomendado es:

```bash
aw-ai runtime install --variant auto
```

`auto` selecciona una variante según el sistema y el hardware detectado. La distribución actual fija `llama.cpp b10903`, commit `481c65f091f74c5e7089dd0a3a1cc6b50cced31e`. Los binarios descargados se verifican por SHA-256 antes de instalarse.

### Linux

En CPU x86_64 o arm64 se utiliza el binario publicado por `llama.cpp` para Ubuntu.

En NVIDIA, el release fijado no publica un binario CUDA de host equivalente al requerido por este proyecto. `aw-ai runtime install --variant nvidia` compila la revisión fijada desde fuente y requiere:

- Git;
- CMake;
- CUDA Toolkit con `nvcc`;
- un compilador compatible con esa toolchain.

La compilación conserva el commit fijado y activa CUDA. El controlador NVIDIA pertenece al sistema anfitrión.

### Windows

En CPU x64 y ARM64 se utilizan binarios publicados por `llama.cpp`.

En NVIDIA x64 se utiliza la variante CUDA 12.4 publicada junto con su paquete de runtime CUDA. Archive Workbench AI verifica los hashes declarados antes de extraerlos.

### macOS

En Apple Silicon e Intel se utilizan los binarios nativos publicados por `llama.cpp`. La variante `metal` es la opción automática en macOS. La disponibilidad de una ruta de instalación no equivale a una validación de calidad/rendimiento de todos los modelos sobre cada Mac.

### Inspección

```bash
aw-ai runtime inspect --json
```

La instalación administrada queda en el directorio de datos de Archive Workbench AI:

- Linux: `${XDG_DATA_HOME:-~/.local/share}/archive-workbench-ai/`;
- macOS: `~/Library/Application Support/archive-workbench-ai/`;
- Windows: `%LOCALAPPDATA%\archive-workbench-ai\`.

Puede cambiarse con `AW_AI_DATA_HOME` o `AW_AI_RUNTIME_HOME`.

## 3. Descargar un modelo

Los pesos no vienen incluidos. Por ejemplo, para H24:

```bash
aw-ai models pull 'ggml-org/gemma-4-26B-A4B-it-GGUF:Q4_0'
```

Para el perfil lógico L12:

```bash
aw-ai models pull 'unsloth/Qwen3.5-9B-GGUF:Q4_K_M'
```

Cada descarga se conserva en el directorio de datos del programa y se verifica con los hashes conocidos por el catálogo.

## 4. Diagnóstico

```bash
aw-ai doctor --json
```

`status: ok` significa que existe un runtime detectable y al menos un modelo instalado. `setup_required` indica que falta alguna de esas capas.

## 5. Integración con Archive Workbench

En una instalación nativa/técnica, Archive Workbench puede descubrir `aw-ai` por `PATH`. También puede fijarse la ruta:

Linux/macOS:

```bash
export ARCHIVE_WORKBENCH_AI_EXECUTABLE=/ruta/a/.venv/bin/aw-ai
```

Windows PowerShell:

```powershell
$env:ARCHIVE_WORKBENCH_AI_EXECUTABLE = "C:\ruta\a\.venv\Scripts\aw-ai.exe"
```

Las imágenes Docker administradas de Archive Workbench todavía no incluyen un puente hacia el proceso nativo del host. No se debe presentar esa combinación como cerrada hasta implementar y validar dicho puente.

## 6. Funcionamiento offline

Después de instalar runtime y modelos, la inferencia no necesita red. Los comandos que sí requieren red son los que descargan explícitamente componentes, como `runtime install` y `models pull`.

## Compatibilidad con instalaciones anteriores

El código conserva lectura de las variables `AW_AI01_*` y, cuando corresponde, del directorio histórico `archive-workbench-ai01` para permitir una transición sin volver a descargar pesos. Las instalaciones nuevas deben usar `AW_AI_*` y `archive-workbench-ai`.


## Integración con la distribución administrada de Archive Workbench

Una vez instalado `aw-ai`, los launchers de Archive Workbench pueden iniciar automáticamente el compañero local. Si el ejecutable no está en `PATH`, puede indicarse su ruta en `ARCHIVE_WORKBENCH_AI_EXECUTABLE`.

El compañero usa como buzón la carpeta `ArchiveWorkbenchData/Settings/archive-workbench-ai-bridge` del bundle de Archive Workbench. Puede comprobarse manualmente con:

```bash
aw-ai bridge status --root /ruta/a/ArchiveWorkbenchData/Settings/archive-workbench-ai-bridge --json
```

La inferencia sigue ejecutándose en el host; Docker sólo intercambia paquetes mediante la carpeta compartida.
