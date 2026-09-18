## 0.1.0.dev24 — Setup gráfico y candidatas nativas

- Agrega Archive Workbench AI Setup como interfaz local sin terminal para estado y preparación explícita de perfiles.
- Impide que la ruta administrada compile Linux/NVIDIA desde fuente; el rechazo precede cualquier reparación destructiva.
- Agrega workflows para construir/smokear candidatas nativas de Ubuntu, Windows y macOS.
- Agrega workflow separado para construir el runtime CUDA Linux x64 desde el commit fijado de llama.cpp.
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
