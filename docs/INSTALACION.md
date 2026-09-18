# Instalación

Archive Workbench AI se instala como un componente separado de Archive Workbench. El ejecutable de la aplicación, el runtime `llama.cpp` y los modelos tienen ciclos de instalación y actualización independientes.

La ruta pública administrada no requiere Python ni terminal. Archive Workbench AI Setup ya implementa la preparación gráfica de runtime/modelo y el estado del compañero local. Los paquetes nativos todavía deben construirse y validarse como candidatas antes del primer release público. Las instrucciones desde fuente de esta sección son sólo para desarrollo y diagnóstico.

## 1. Instalación técnica desde fuente

Requiere Python 3.11 o posterior:

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


## Archive Workbench AI Setup

El Setup administrado es una interfaz local abierta en el navegador por el ejecutable nativo. Escucha únicamente en `127.0.0.1`, no usa recursos web externos y requiere una autorización efímera para las acciones que modifican la instalación. La vista de estado es pasiva: abrirla no instala runtime, no descarga modelos y no inicia inferencia.

Las acciones visibles permiten preparar L12/H24, comprobar o reparar el runtime, activar el compañero local y descargar un diagnóstico. Sólo una operación de instalación se ejecuta a la vez.

## 2. Instalar el runtime local

En instalación técnica, el comando es:

```bash
aw-ai runtime install --variant auto
```

Archive Workbench AI Setup ofrece la operación equivalente mediante interfaz gráfica en la distribución administrada. `auto` selecciona una variante según el sistema y el hardware detectado. La distribución actual fija `llama.cpp b10903`, commit `481c65f091f74c5e7089dd0a3a1cc6b50cced31e`. Los binarios descargados se verifican por SHA-256 antes de instalarse.

### Linux

En CPU x86_64 o arm64 se utiliza el binario publicado por `llama.cpp` para Ubuntu.

En NVIDIA, el release upstream fijado no publica un binario CUDA de host equivalente al requerido por este proyecto. La ruta técnica desde fuente todavía puede compilar la revisión fijada con Git, CMake, CUDA Toolkit y un compilador compatible. **Archive Workbench AI Setup no ejecuta esa compilación.** El workflow administrado construye fuera del equipo usuario un runtime NVIDIA candidato; sólo después de verificarlo y fijar su SHA-256 se incorporará al catálogo. El controlador NVIDIA seguirá perteneciendo al sistema anfitrión.

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

Los pesos no vienen incluidos. En la distribución administrada, Archive Workbench AI Setup realiza la descarga explícita elegida por la persona usuaria y conserva la verificación de integridad. En instalación técnica, por ejemplo para H24:

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

La distribución administrada usa un buzón global por usuario bajo el directorio de datos de Archive Workbench AI. El launcher de Archive Workbench encuentra la instalación nativa canónica, inicia el compañero y monta únicamente ese buzón en Docker. No hace falta configurar `PATH` ni variables de entorno en el recorrido de usuario.

`PATH` y `ARCHIVE_WORKBENCH_AI_EXECUTABLE` se conservan sólo para desarrollo/diagnóstico.

El bridge puede consultarse técnicamente con `aw-ai bridge status`; esto no forma parte de la validación manual de usuario.

## 6. Funcionamiento offline

Después de instalar runtime y modelos, la inferencia no necesita red. Los comandos que sí requieren red son los que descargan explícitamente componentes, como `runtime install` y `models pull`.

## Compatibilidad con instalaciones anteriores

El código conserva lectura de las variables `AW_AI01_*` y, cuando corresponde, del directorio histórico `archive-workbench-ai01` para permitir una transición sin volver a descargar pesos. Las instalaciones nuevas deben usar `AW_AI_*` y `archive-workbench-ai`.


## Integración administrada

El compañero local usa por defecto `aw-ai bridge path` para resolver su buzón global. Archive Workbench monta ese directorio dentro del contenedor y sólo intercambia EXP-01, result y handoff. El bridge no abre un puerto de red ni accede a SQLite. Los trabajos consumidos se eliminan automáticamente; fallos y resultados no consumidos tienen retención acotada para diagnóstico/recuperación.
