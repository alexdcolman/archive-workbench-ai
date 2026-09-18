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
