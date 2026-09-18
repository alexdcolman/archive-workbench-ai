# Archive Workbench AI

Motor externo e independiente de análisis asistido para Archive Workbench para ejecutar y comparar `vision_describe/0.1` mediante runtimes/modelos locales.

P0 validó el protocolo con backend simulado. P1 cerró el circuito real con `llama.cpp` + MiniCPM-V 4.6 sobre RTX 3090. P2 cerró la selección lógica de modelos y el soporte de contexto espacial de EXP-01 1.1. P3 agrega el handoff propositivo AI→AW como frontera versionada; la persistencia y revisión pertenecen a Archive Workbench.

Principios:

- Archive Workbench y Archive Workbench AI se distribuyen por separado.
- `run` y `benchmark run` son offline y usan un servidor efímero en `127.0.0.1`.
- `models pull` es la única operación que descarga pesos.
- Los pesos se verifican por SHA-256.
- Los modelos se cargan secuencialmente.
- Diagnósticos: `AWAI_DIAGNOSTICO_*.zip` en `~/Downloads/`.
- Benchmarks: `AWAI_BENCHMARK_*.zip` en `~/Downloads/`.
- EXP-01 1.0 sigue admitido para evidencia histórica y jobs visuales sin contexto.
- EXP-01 1.1 aporta texto canónico + `geometry` + `bbox` normalizado por objeto textual.

## Criterio de `vision_describe/0.1` desde dev16

La imagen sigue siendo evidencia primaria para composición y rasgos visuales/documentales. Cuando EXP-01 1.1 aporta texto canónico localizado, ese texto se usa como contexto ya disponible y **no como OCR a rehacer**. La evaluación prioriza organización material, sellos, firmas, manuscritos, casillas, superposiciones, deterioro, jerarquía visual, relaciones texto/imagen e inferencias no justificadas. La recuperación textual exhaustiva deja de ser un criterio principal.

## Estado de modelos

- **L12 lógico cerrado:** Qwen3.5-9B Q4_K_M es la configuración principal por calidad visual/documental; Gemma E4B queda como fallback rápido y MiniCPM-V 4.6 como baseline. Falta sólo la validación en GPU física de 12 GB.
- **H24 cerrado:** Gemma 4 26B-A4B Q4_0 es la configuración principal por equilibrio entre precisión estructural/documental, tiempo y margen de VRAM.
- Qwen3.6 35B-A3B Q4_K_M queda como referencia de mayor detalle visual con mayor coste.
- Gemma 4 E4B Q4_0 queda como fallback liviano; no es principal H24 porque cometió un error estructural relevante en la página periodística.

## dev16 — EXP-01 1.1

Archive Workbench AI acepta EXP-01 1.0 y 1.1. Para 1.1 valida `context/objects.jsonl`, el hash declarado y el contrato `x_y_width_height` en espacio `normalized`, asocia los objetos de contexto a cada página y construye un prompt efectivo con texto + bbox. La configuración efectiva registra cuántos bloques contextuales recibió cada target y si el contexto fue truncado por el límite determinista del plugin.

Ver `docs/PROTOCOLO_0_1.md`, `docs/BENCHMARK_P1_P2_20260915.md` y `docs/INSTALACION_P2.md`.


## dev16 — disciplina de contexto y salida

La primera corrida EXP-01 1.1 real mostró que algunos modelos podían convertir el texto canónico en una retranscripción extensa. dev16 conserva texto+bbox como contexto, pero recorta determinísticamente cada bloque largo para el prompt y limita la estructura generada. Si una primera generación termina por longitud, el retry usa una instrucción compacta explícita. El schema público `vision_describe/0.1` no cambia.

## Mini benchmark público

La batería H24 de cierre se publica en formato repo-agnóstico bajo `benchmarks/vision-describe-h24-20260915/`: incluye las dos capturas, métricas, request y salidas estructuradas de los tres modelos. El directorio puede copiarse tal cual al futuro repositorio público aunque cambie su nombre.

La batería L12 pública está en `benchmarks/vision-describe-l12-20260915/`.


## P3 — handoff de resultados propuestos

Desde `0.1.0.dev18`, el motor puede convertir un `result.zip` completo y su EXP-01 original en un paquete
`archive_workbench_ai_result_handoff/0.1`. El paquete conserva IDs de target, documento/página, hashes de
EXP-01 y result bundle, modelo, runtime, prompt y salida estructurada. Su política es siempre
`proposed_only`: no aplica cambios automáticamente y exige revisión humana en Archive Workbench.

```bash
aw-ai handoff build --input EXP01.zip --result result.zip --output handoff.zip
aw-ai handoff inspect --bundle handoff.zip --json
```

Archive Workbench AI sigue sin abrir SQLite ni importar módulos internos de Archive Workbench. Del lado AW, P3-A, P3-B y la candidata P3-C consumen este mismo handoff dev18 sin ampliarlo: P3-B persiste raw + revisión humana en `0049_external_analysis_layer` y P3-C agrega la sección top-level `Análisis asistido` para recibir, revisar y consultar esa capa.

`capabilities --json` distingue el baseline de bootstrap (`default_model`) de los defaults de calidad por perfil (`profile_default_models`): Qwen3.5 9B para L12 y Gemma 26B-A4B para H24.

## dev20 — nombre público estable y análisis completo

Para el uso normal ya no hace falta construir `request.json`, dividir páginas ni ejecutar `handoff build` por cada tanda. `analyze` recibe directamente un EXP-01 y genera un único resultado/handoff consolidado:

```bash
aw-ai analyze \
  --input /ruta/EXP01.zip \
  --profile H24
```

Si se omite `--output`, el handoff se guarda en `~/Downloads/AWAI_HANDOFF_<timestamp>.zip` y el result bundle queda junto a él. El perfil elige su modelo default (H24 → Gemma 4 26B-A4B Q4_0; L12 → Qwen3.5 9B Q4_K_M), aunque `--model` permite una selección explícita.

El contrato bajo nivel `archive-workbench-ai/0.1` continúa admitiendo 1–3 targets por request. dev20 conserva ese límite en un detalle interno: registra los requests internos por lotes, mantiene la trazabilidad y entrega un único handoff `archive_workbench_ai_result_handoff/0.1` con todas las propuestas. `aw-ai run` sigue disponible para reproducción y depuración fina.


## dev20 — nombre público estable

El proyecto adopta el nombre público **Archive Workbench AI**. El paquete distribuible es `archive-workbench-ai`, el módulo Python es `archive_workbench_ai` y la CLI es `aw-ai`. Los contratos versionados no cambian: el protocolo sigue siendo `archive-workbench-ai/0.1` y el handoff sigue siendo `archive_workbench_ai_result_handoff/0.1`.

La instalación dev20 reconoce como compatibilidad local el almacenamiento y las variables `AW_AI01_*` de las candidatas previas, para reutilizar modelos y runtime ya descargados. Las instalaciones nuevas usan `AW_AI_*` y `~/.local/share/archive-workbench-ai/`.
