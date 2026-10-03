## 0.1.0.dev29 — promoción del runtime Linux/NVIDIA validado

- Fija el catálogo Linux x86_64/NVIDIA al asset inmutable `runtime-b10903-linux-nvidia-20261001` publicado en `alexdcolman/archive-workbench-ai-dist`.
- Actualiza el SHA-256 administrado a `b0b02cf52a910e1ec1addf58491c9896dd73c06383e0d5ba8884a852658e56bf`, verificado nuevamente tras descargar el asset desde la release pública.
- Registra como cerrados el smoke nativo dev28 y la validación integrada Linux con `bridge start` normal, que produjo 18 propuestas desde Archive Workbench.
- No recompila llama.cpp, no cambia modelos, protocolos, handoff ni imágenes Docker de Archive Workbench.

## 0.1.0.dev28 — lifecycle del bridge PyInstaller onefile

- El daemon congelado iniciado por `bridge start` se relanza como instancia PyInstaller independiente mediante `PYINSTALLER_RESET_ENVIRONMENT=1`, evitando que pierda prompts/esquemas cuando termina el proceso iniciador y se elimina su `_MEI`.
- El workflow nativo conserva el smoke directo `analyze --backend mock` y agrega un smoke de daemon que crea un job después de terminar `bridge start`, exige que el bridge siga vivo y rechaza errores de recursos `_MEI`.
- El runtime NVIDIA dev27, modelos, protocolo y handoff no cambian.

## 0.1.0.dev26 — runtime NVIDIA sin NCCL y diagnóstico estricto

- recompila el candidato Linux/NVIDIA de llama.cpp b10903 con `GGML_CUDA_NCCL=OFF` para eliminar la dependencia accidental de `libnccl.so.2`;
- valida el tar candidato fuera de la imagen CUDA de compilación y rechaza dependencias compartidas no resueltas distintas de `libcuda.so.1`, provista por el driver del host;
- `detect_runtime` deja de declarar disponible un ejecutable cuyo `--version` termina con error y conserva el detalle de los probes fallidos en `runtime inspect`/`doctor`;
- no cambia protocolos, handoff, modelos ni el catálogo publicado hasta construir y verificar el nuevo runtime candidato.

## 0.1.0.dev27 — runtime NVIDIA autocontenido con OpenMP

- Mantiene `GGML_CUDA_NCCL=OFF` y el gate externo introducido en dev26.
- Empaqueta `libgomp.so.1` junto al runtime Linux/NVIDIA para conservar OpenMP sin exigir dependencias de sistema al usuario.
- Incluye el aviso de copyright/licencia de `libgomp1` dentro del tar administrado.
- El gate en Ubuntu 24.04 limpio sigue admitiendo como única dependencia no resuelta `libcuda.so.1`, provista por el driver NVIDIA del host.
- El catálogo público permanece sin cambios hasta obtener SHA-256 y validación física del nuevo candidato.

## 0.1.0.dev25 — reparación del análisis en binarios nativos

- Corrige la carga del prompt `vision_describe_0_1.txt` en ejecutables PyInstaller sin depender del submódulo dinámico `archive_workbench_ai.prompts`.
- Agrega un smoke obligatorio de `analyze --backend mock` sobre el binario congelado en Linux, Windows y macOS.
- Mantiene sin cambios los protocolos, el handoff, el runtime `llama.cpp b10903` y los modelos instalados fuera del ejecutable.

## 0.1.0.dev24 — Setup gráfico y candidatas nativas

- Agrega Archive Workbench AI Setup como interfaz local sin terminal para estado y preparación explícita de perfiles.
- Impide que la ruta administrada compile Linux/NVIDIA desde fuente; el rechazo precede cualquier reparación destructiva.
- Agrega workflows para construir/smokear candidatas nativas de Ubuntu, Windows y macOS.
- Agrega workflow separado para construir el runtime CUDA Linux x64 desde el commit fijado de llama.cpp.
- Cierra el runtime NVIDIA Linux x64 precompilado con SHA-256 `d41bb204eb09995bfe387950435ddd84635aaaed28fade425d7d35c1bb2cee89` y lo registra para descarga administrada desde `archive-workbench-ai-dist`.
- Mantiene runtime/modelos fuera del ejecutable y conserva el bridge global de dev23.

## 0.1.0.dev23 — base de distribución administrada sin terminal

- fija un buzón global por usuario para el bridge;
- agrega ruta administrada consultable mediante `aw-ai bridge path`;
- hace compatible el arranque del companion con ejecutables congelados;
- elimina automáticamente jobs consumidos y acota la retención de fallos/resultados no consumidos;
- define ubicaciones canónicas de instalación por sistema para la futura aplicación nativa;
- documenta como gate obligatorio la validación manual sin terminal.

# Changelog

## Unreleased

### Preparación del release público

- La documentación pública vigente describe el producto y la integración sin depender de nombres internos de fases o revisiones de desarrollo.
- El README y `FIRST_START.txt` de Archive Workbench quedan preparados para explicar el componente opcional y el puente local; la página dedicada del sitio público se difiere hasta que las imágenes e integración estén cerradas.
- Continúan pendientes la validación manual final con imágenes publicadas en Windows CPU, Ubuntu CPU y Ubuntu GPU NVIDIA, la validación física L12 en una GPU real de 12 GB y la revisión de derechos antes de publicar imágenes archivísticas de benchmark.

## 0.1.0.dev22 — puente local para Archive Workbench administrado

- agrega `aw-ai bridge init/start/status/stop/serve`;
- incorpora buzón local autenticado y sin puertos para Docker ↔ motor nativo;
- conserva EXP-01/handoff como frontera y no expone SQLite ni rutas arbitrarias;
- integra el transporte de puente en Archive Workbench mediante `ARCHIVE_WORKBENCH_AI_BRIDGE_DIR`;
- mantiene pendiente la validación manual final sobre las imágenes publicadas.

Los cambios públicos de Archive Workbench AI se registran en este archivo.
