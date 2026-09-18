# Protocolo `archive-workbench-ai/0.1`

La implementación vigente admite únicamente `vision_describe/0.1` sobre 1–3 assets de un paquete EXP-01 (`page`, `region` o `figure`). El protocolo AI no cambia en dev16.

## EXP-01 admitidos

- **1.0:** compatible para evidencia histórica y jobs visuales sin contexto espacial textual.
- **1.1:** contrato preferido desde Archive Workbench 1.2.0. Además de los assets visuales, `context/objects.jsonl` puede aportar texto canónico, `geometry` y `bbox` normalizado por objeto textual.

Para EXP-01 1.1 Archive Workbench AI valida:

- SHA-256 del ZIP completo;
- `package_type`;
- `schema_version`;
- identidad/tipo de cada target;
- SHA-256 y tamaño del asset seleccionado;
- SHA-256 de `context/objects.jsonl`;
- contrato `object_geometry` del manifest;
- `bbox` en espacio `normalized`, formato `x_y_width_height`.

El plugin no abre SQLite ni rutas internas del proyecto. La asociación entre imagen y texto espacial se deriva sólo del paquete EXP-01.

## Semántica de `vision_describe/0.1`

La imagen es evidencia primaria de percepción visual/documental. Si existe contexto canónico 1.1, el modelo recibe texto + bbox como información ya disponible. No debe hacer OCR redundante ni ser premiado por retranscribir exhaustivamente el texto canónico. `visible_text_notes` queda reservado para texto cuya forma, posición, superposición, discrepancia o incertidumbre sea relevante visualmente.

El contexto textual por target se serializa de manera determinista y se limita a 12.000 caracteres para preservar margen de inferencia. `effective_configuration` registra `exp01_context_objects` y `exp01_context_truncated`.

`result.zip` conserva `manifest.json`, `results/items.jsonl`, `prompts/effective_prompt.txt`, `metrics/runtime.json` y `raw/responses.jsonl`.

`benchmark prepare` sigue pudiendo construir un EXP-01 1.0 válido desde 1–3 imágenes locales; ese comando sirve para pruebas visuales aisladas y no reemplaza una exportación 1.1 producida por Archive Workbench.
