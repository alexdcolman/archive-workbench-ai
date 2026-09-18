# Protocolo `archive-workbench-ai/0.1`

El protocolo 0.1 define la frontera de bajo nivel entre un paquete EXP-01 y una tarea ejecutada por Archive Workbench AI. El uso cotidiano desde Archive Workbench se realiza mediante `aw-ai analyze`, que administra esta capa internamente.

## Tarea disponible

La tarea pública actual es `vision_describe/0.1` sobre assets de tipo `page`, `region` o `figure`.

Un request 0.1 admite entre uno y tres targets. Ese límite pertenece al contrato de bajo nivel. `aw-ai analyze` puede recorrer un EXP-01 completo, dividirlo internamente en requests compatibles y producir un único result bundle y un único handoff consolidados.

## EXP-01

Se admiten:

- **EXP-01 1.0**, para compatibilidad con evidencia histórica y jobs visuales sin contexto espacial textual;
- **EXP-01 1.1**, formato preferido de Archive Workbench 1.2.0, con posibilidad de incluir texto canónico y geometría mediante `context/objects.jsonl`.

Para EXP-01 1.1 se valida la identidad de los targets, hashes y tamaños de assets, el contexto declarado y el contrato de geometría.

Archive Workbench AI procesa sólo el contenido del paquete. No abre rutas internas del proyecto Archive Workbench ni su base SQLite.

## Semántica de `vision_describe/0.1`

La imagen es evidencia primaria para la descripción visual/documental. Cuando EXP-01 1.1 incluye texto canónico localizado, ese texto se trata como contexto ya disponible y no como OCR a rehacer.

La tarea se concentra en estructura material y visual, sellos, firmas, manuscritos, casillas, superposiciones, deterioro, jerarquía y relaciones espaciales. `visible_text_notes` se reserva para texto cuya forma, posición, discrepancia o incertidumbre sea visualmente relevante.

El contexto se serializa de manera determinista y puede truncarse para preservar margen de inferencia. La configuración efectiva registra esa decisión para mantener trazabilidad.

## Resultado

Un result bundle conserva, entre otros elementos:

- manifiesto de la corrida;
- resultados estructurados por target;
- prompt efectivo;
- métricas de runtime;
- respuestas crudas necesarias para diagnóstico y trazabilidad.

## Handoff

`archive_workbench_ai_result_handoff/0.1` es el contrato que Archive Workbench consume para presentar propuestas. El handoff conserva la relación con el EXP-01, el resultado, el modelo y el runtime utilizados.

Su política es siempre propositiva. El handoff no autoriza a Archive Workbench AI a modificar la base de datos y no equivale a una aceptación humana.

## Red

La ejecución de `run`, `analyze` y benchmarks con componentes ya instalados usa únicamente el runtime local. Las descargas de runtime o modelos son operaciones explícitas y separadas.
