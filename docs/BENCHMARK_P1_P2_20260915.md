# AI-01 — benchmark P1/P2: evidencia, resultados y estado de evaluación

> Nota de nombre: **AI-01** era la denominación de desarrollo. El proyecto se denomina actualmente **Archive Workbench AI**. Los nombres de artefactos e identificadores históricos de esta evidencia se conservan sin reescribir.


**Fecha de consolidación:** 2026-09-15.  
**Plugin vigente:** `archive-workbench-ai01 0.1.0.dev16`.  
**Fase:** P2 activa. P1 cerrado técnicamente.  
**Tarea evaluada:** `vision_describe/0.1`.  
**Protocolo:** `archive-workbench-ai/0.1`.

## 1. Alcance de este documento

Este documento reemplaza como estado canónico a `BENCHMARK_P1_P2_20260914.md` sin borrar ese corte histórico. Consolida la evidencia desde P1 hasta la comparación H24 de Gemma 4 26B-A4B y Qwen3.6-35B-A3B sobre el corpus sintético común.

Todavía **no cierra la selección definitiva de modelos**. La batería sintética ya permite cerrar viabilidad técnica y una primera comparación cualitativa; antes de promover un default H24 falta una batería ampliada con páginas archivísticas reales o material de dificultad equivalente.

## 2. Entorno canónico de las corridas reales

- GPU: NVIDIA GeForce RTX 3090.
- VRAM total informada: 24.576 MiB.
- Driver NVIDIA: `580.173.02`.
- Plataforma: `Linux-7.0.0-30-generic-x86_64-with-glibc2.39`.
- Python: `3.12.3`.
- Runtime: `llama.cpp b10903`, commit `481c65f`.
- `llama-server --version`: `0.4.0-dev (build 1, commit 481c65f)`.
- Runtime validado por el plugin como `pinned` por coincidencia exacta de commit.
- `run` y `benchmark run` son offline; el servidor efímero escucha sólo en `127.0.0.1`.
- Los modelos se cargan secuencialmente.

## 3. Corpus sintético común P2

Las comparaciones L12/H24 cerradas hasta este corte usan el mismo EXP-01 (`sha256 e491d2128eb43aff0d0b3d3dec31ff5c0eab0f1483e84ce6c0d1920f12134b19`) y tres páginas:

1. `page:ai01-p2-bench:1`: memorando limpio, tabla, sello y firma simulada.
2. `page:ai01-p2-bench:2`: copia degradada, fecha parcialmente ilegible, anotación marginal, sello superpuesto y número de registro.
3. `page:ai01-p2-bench:3`: ficha administrativa con campos estructurados, casilla marcada/desmarcada, texto pequeño y sello.

Parámetros comunes: temperatura `0.0`, seed `0`, presupuesto solicitado `512` tokens, `offline_required` y schema `vision_describe/0.1`.

## 4. P1 — estabilización del circuito real

P1 se cerró con MiniCPM-V 4.6 Q4_K_M sobre RTX 3090. Están resueltos y no deben reabrirse sin una regresión concreta:

- validación del runtime por commit `481c65f`;
- descargas con 429/reintentos/reanudación `.part`;
- diagnóstico compartible automático en `~/Downloads/`;
- `enable_thinking=false` para `vision_describe`;
- `response_format.json_schema.schema`;
- expansión auditada del presupuesto ante `finish_reason=length`.

## 5. Estado L12

La batería L12 queda cerrada provisionalmente:

| Modelo | Estado | Tiempo total | Pico VRAM | Pico RAM | Generación media |
|---|---:|---:|---:|---:|---:|
| MiniCPM-V 4.6 Q4_K_M | complete | 6,879 s | 1.704 MiB | 1.071 MiB | 284,35 tok/s |
| Gemma 4 E4B-it Q4_0 | complete | 14,251 s | 4.398 MiB | 4.765 MiB | 117,33 tok/s |
| Qwen3.5-9B Q4_K_M | complete | 31,479 s | 6.680 MiB | 5.574 MiB | 99,73 tok/s |

Gemma 4 E4B sigue como candidato L12 principal provisional por fidelidad y disciplina descriptiva; MiniCPM queda como baseline mínimo y Qwen3.5-9B no lo desplaza. Falta validar límite efectivo de 12 GB y, cuando sea posible, una GPU física de 12 GB antes de promover `supported`.

## 6. H24 — Gemma 4 26B-A4B

La secuencia dev10-dev13 queda cerrada:

- dev11 identificó que `n_gpu_layers=999` impedía actuar a `--fit`; se eliminó el pin y H24 reserva 3072 MiB mediante `--fit-target`;
- dev12 identificó el assert de atención visual no causal con `ubatch` insuficiente;
- dev13 aplica a Gemma 4 multimodal `batch_size=2048` / `ubatch_size=2048`.

`AI01_BENCHMARK_20260915T000508Z.zip` completó 3/3 targets:

- total: **21,032 s**;
- carga servidor/modelo: **5.551 ms**;
- pico VRAM: **16.774 MiB**;
- pico RSS: **14.325 MiB**;
- generación media: **118,77 tok/s**;
- red durante inferencia: `false`.

Cualitativamente, el 26B recuperó correctamente los elementos centrales de las tres páginas. En la página degradada agregó una inferencia no estrictamente visual sobre que la pieza parecía una transcripción o descripción técnica de una copia de baja calidad. La viabilidad técnica H24 queda comprobada; la ventaja cualitativa sobre E4B no queda demostrada por esta muestra sola.

## 7. H24 — Qwen3.6-35B-A3B

Artefactos verificados:

- modelo `Qwen3.6-35B-A3B-Q4_K_M.gguf`: SHA-256 `671e47e0ec53c665d048b98c3ecbfd5236b5ca9c3e02ed19fc8f81f7b85140c7`;
- mmproj `mmproj-Qwen3.6-35B-A3B-Q8_0.gguf`: SHA-256 `904cbf8c8e876220066ab3bf676c7efa40f3da372276fdaf8b01d2fb2a37a51d`.

Benchmark `AI01_BENCHMARK_20260915T032333Z.zip` sobre el mismo request H24:

- estado: `complete`;
- targets: 3/3;
- tiempo total: **52,043 s**;
- carga servidor/modelo: **23.073 ms**;
- pico VRAM: **19.624 MiB**;
- pico RSS: **19.257 MiB**;
- generación media: **101,23 tok/s**;
- red durante inferencia: `false`;
- `--fit on`, `fit_target_mib=3072`, `n_gpu_layers_policy=auto_unpinned`, KV `q8_0/q8_0`, Flash Attention `on`, mmproj offload activo.

El presupuesto se amplió automáticamente de 512 a 1024 tokens por `finish_reason=length`; la corrida terminó con JSON válido y sin reparación estructurada.

### Evaluación cualitativa

- página 1: lectura correcta y detallada, pero añade incertidumbres metadocumentales innecesarias sobre autenticidad, carácter ficticio y emisor;
- página 2: muy buena recuperación de fecha parcial, `revisar folio 3`, `MESA DE ENTRADAS` y `0042-AX`; es su mejor salida de la muestra;
- página 3: recupera campos, casillas, clasificación, control de acceso y sello, pero simultáneamente afirma que parte de la sección final no es visible/legible y duda de que ciertas marcas estén realmente presentes, pese a haberlas descrito.

Conclusión: **Qwen3.6 es técnicamente viable en H24 pero no desplaza a Gemma 26B ni a E4B en esta batería**. Consume más memoria, tarda sustancialmente más y presenta más incertidumbres no necesarias para una tarea de descripción visual estricta.

## 8. Comparación H24 sintética cerrada

| Métrica | Gemma E4B (dev10) | Gemma 26B-A4B (dev13) | Qwen3.6-35B-A3B (dev13) |
|---|---:|---:|---:|
| Estado | complete | complete | complete |
| Tiempo total | 15,380 s | 21,032 s | 52,043 s |
| Pico VRAM | 4.506 MiB | 16.774 MiB | 19.624 MiB |
| Pico RAM | 4.760 MiB | 14.325 MiB | 19.257 MiB |
| Generación media | 117,35 tok/s | 118,77 tok/s | 101,23 tok/s |

Sobre estas tres páginas, E4B conserva el mejor equilibrio de coste y disciplina descriptiva. Gemma 26B queda como candidato H24 de mayor capacidad, pero todavía necesita demostrar una mejora de calidad consistente sobre material archivístico más exigente. Qwen3.6 queda evaluado y no preferido para este vertical en la configuración probada.

La corrida Qwen3.6 completó con ~4.952 MiB de margen respecto de los 24.576 MiB informados por la GPU. Por tanto, **no se abre ahora una variante `--cpu-moe` / `--n-cpu-moe`**: `--fit` fue suficiente y no existió presión de VRAM que justifique esa rama.

## 9. dev14 — preparación reproducible del corpus ampliado

`0.1.0.dev14` no cambia el protocolo `archive-workbench-ai/0.1` ni la inferencia. Agrega una utilidad P2 para construir un job reproducible desde 1–3 imágenes locales:

```bash
aw-ai benchmark prepare \
  --profile H24 \
  --images PAGINA_1.tiff PAGINA_2.tiff PAGINA_3.tiff
```

El comando:

- acepta formatos de imagen que Pillow pueda abrir, incluido TIFF de una sola página;
- rechaza silencios ambiguos: un TIFF/imagen multipágina debe separarse antes en páginas individuales;
- normaliza cada target a PNG sin redimensionar;
- conserva en `job_manifest.json` nombre de archivo, SHA-256 original, tamaño, formato y dimensiones, sin guardar la ruta absoluta local;
- genera por defecto `~/Downloads/AI01_BENCHMARK_JOB_<timestamp>.zip`;
- incluye `request.json` + `exp01.zip` válidos para el protocolo 0.1.

El job puede ejecutarse directamente:

```bash
aw-ai benchmark run \
  --job ~/Downloads/AI01_BENCHMARK_JOB_<timestamp>.zip \
  --models \
    'ggml-org/gemma-4-E4B-it-GGUF:Q4_0' \
    'ggml-org/gemma-4-26B-A4B-it-GGUF:Q4_0' \
    'ggml-org/Qwen3.6-35B-A3B-GGUF:Q4_K_M'
```

La razón explícita para repetir E4B/26B/Qwen3.6 en esa próxima corrida es que **cambia el corpus de evaluación**. No se repite la batería sintética cerrada.

## 10. Estado canónico después de dev14

### Cerrado / comprobado

- P1 real: cerrado.
- protocolo 0.1 y JSON estructurado: estables.
- diagnósticos y benchmark compartibles en `~/Downloads/`: vigentes.
- L12 sintético: MiniCPM / E4B / Qwen3.5 completado.
- Gemma 26B-A4B: viabilidad H24 comprobada.
- Qwen3.6-35B-A3B: viabilidad H24 comprobada; evaluado/no preferido en el corpus sintético.
- fallos `n_gpu_layers=999` y `ubatch=512`: resueltos.
- no se requiere por ahora una variante CPU-MoE.
- existe un generador reproducible de jobs desde páginas locales para ampliar la evaluación sin tocar Archive Workbench.

### Abierto

1. seleccionar 1–3 páginas archivísticas reales o material de dificultad equivalente y generar un job dev14;
2. ejecutar sobre ese mismo job E4B, Gemma 26B y Qwen3.6 y comparar calidad, omisiones, alucinaciones e incertidumbres;
3. decidir el default H24 sólo después de esa batería ampliada;
4. validar L12 bajo límite efectivo de 12 GB y, cuando sea posible, GPU física de 12 GB;
5. después de estabilizar modelos/configuraciones, avanzar a P3 de exportación/importación con Archive Workbench;
6. AI-02 permanece posterior a la estabilización de AI-01.

## 11. Evidencia canónica

Bajo `evidence/benchmarks/` se conservan:

- `AI01_BENCHMARK_20260912T203219Z.zip` — dev9 MiniCPM vs E4B;
- `AI01_BENCHMARK_20260912T220922Z.zip` — dev9 MiniCPM vs E4B vs Qwen3.5;
- `AI01_BENCHMARK_20260913T004809Z.zip` — dev10 H24 parcial;
- `AI01_BENCHMARK_20260913T021313Z.zip` — dev11 OOM diagnosticado;
- `AI01_BENCHMARK_20260914T235124Z.zip` — dev12 carga OK / assert visual;
- `AI01_BENCHMARK_20260915T000508Z.zip` — dev13 H24 Gemma 26B completo;
- `AI01_BENCHMARK_20260915T032333Z.zip` — dev13 H24 Qwen3.6 completo;
- `Archive_Workbench_AI01_P2_BENCHMARK_JOB_20260912.zip` — corpus sintético común.

Los ZIP de evidencia no son una segunda lista de pendientes y no deben ejecutarse de nuevo por rutina.


## Corrección metodológica — EXP-01 1.1 / dev16

La primera evaluación archivística real mostró que el criterio usado inicialmente daba demasiado peso a la recuperación de contenido textual desde la imagen. Eso no representa el uso final previsto: Archive Workbench 1.2.0 amplió EXP-01 a schema 1.1 y exporta, para los objetos textuales, texto canónico, geometría editable y bbox normalizado.

Desde dev16, `vision_describe/0.1` usa ese texto+bbox como contexto ya disponible y mantiene la imagen como evidencia primaria. La recuperación textual exhaustiva deja de ser una ventaja principal. Se evalúan sobre todo estructura material/visual, jerarquía, sellos, firmas, manuscritos, casillas, superposiciones, deterioro, relaciones espaciales texto/imagen e inferencias no justificadas.

Consecuencia: las corridas anteriores siguen siendo evidencia técnica y cualitativa útil, pero no cierran la selección final de modelo. La siguiente comparación H24 debe realizarse con un EXP-01 1.1 real exportado por Archive Workbench y el mismo input para E4B, Gemma 26B y Qwen3.6. No se repiten las baterías históricas 1.0.


## 12. Batería EXP-01 1.1 real y corrección dev16

Benchmark `AI01_BENCHMARK_20260915T170848Z.zip`, ejecutado con Archive Workbench 1.2.0 / EXP-01 1.1 sobre dos páginas reales (`15 A.C 21` y `15 A.C 100`):

- Gemma 26B-A4B: `complete`, 2/2 targets; 27,344 s; pico GPU 16.948 MiB; salida visual/documental disciplinada.
- Qwen3.6-35B-A3B: `complete`, 2/2 targets; 54,254 s; pico GPU 20.352 MiB; segundo target excesivamente verboso y con rasgos duplicados; requirió ampliación 512→1024.
- Gemma E4B: `failed` en el segundo target; no fue fallo de carga ni de EXP-01. Copió extensamente el texto canónico en `visible_text_notes` y agotó 1024 tokens (`finish_reason=length`).

El diagnóstico demuestra un defecto de disciplina del prompt dev15, no del contrato EXP-01 1.1. dev16 corrige sólo esa capa:

- cada bloque canónico largo se representa en el prompt mediante un extracto determinista de hasta 420 caracteres, conservando bbox y orden;
- la salida pide 2–4 oraciones de descripción, máximo 4 `visible_text_notes`, 8 `document_features` y 3 `uncertainties`;
- el JSON Schema interno de generación impone esos máximos de listas, sin cambiar el schema público `vision_describe/0.1`;
- si el primer intento termina por longitud, el segundo agrega una instrucción compacta explícita;
- la configuración efectiva registra cuántos bloques textuales fueron recortados y el tamaño del contexto inyectado.

Este era el estado inmediatamente anterior a la repetición dev16. La comparación común ya fue ejecutada y la selección H24 queda cerrada en la sección 13; no repetir esta batería salvo regresión o cambio material.


## 13. Cierre H24 con dev16

La repetición común `AI01_BENCHMARK_20260915T171823Z.zip` usa el mismo EXP-01 1.1 real, el mismo request y dev16 para los tres modelos. Resultado: **3/3 modelos completos, 2/2 targets por modelo, sin expansión automática del presupuesto de salida**.

| Modelo | Estado | Tiempo total | Pico GPU | Resultado cualitativo |
|---|---:|---:|---:|---|
| Gemma 4 E4B Q4_0 | 2/2 | 13,07 s | 4.976 MiB | Muy liviano, pero describe erróneamente el recorte periodístico de dos columnas como columna única. |
| **Gemma 4 26B-A4B Q4_0** | **2/2** | **23,30 s** | **16.948 MiB** | **Mejor equilibrio**: reconoce hoja + recorte, dos columnas, mecanografía, manuscritos y marcas documentales con buena disciplina. |
| Qwen3.6 35B-A3B Q4_K_M | 2/2 | 38,41 s | 20.352 MiB | Mayor detalle fino, en especial marcas marginales y calidad de impresión, con mayor coste de tiempo y VRAM. |

### Decisión H24

- **Default H24:** `ggml-org/gemma-4-26B-A4B-it-GGUF:Q4_0`.
- **Referencia de mayor detalle:** `ggml-org/Qwen3.6-35B-A3B-GGUF:Q4_K_M`.
- **Fallback liviano:** `ggml-org/gemma-4-E4B-it-GGUF:Q4_0`.

La decisión no se basa sólo en rendimiento. E4B conserva una ventaja grande de coste pero incurre en un error estructural relevante. Qwen3.6 aporta detalle adicional, pero utiliza ~3,4 GiB más de VRAM que Gemma 26B y tarda ~65 % más en esta batería. Gemma 26B ofrece el mejor balance para la tarea documental prevista.

La corrección dev16 resolvió el defecto de disciplina observado en dev15: E4B y Qwen3.6 ya no agotan el presupuesto por retranscripción del contexto canónico. **No se abre dev17 por este problema.**

### Evidencia pública

Se preparó un mini benchmark repo-agnóstico en `benchmarks/vision-describe-h24-20260915/` con las dos capturas, métricas, request y salidas completas. Está pensado para incorporarse al futuro repositorio público sin depender de su nombre.

### Próximo gate

H24 queda cerrado. El siguiente pendiente P2 es L12: validar el candidato bajo un límite efectivo de 12 GB y, cuando sea posible, en una GPU física de 12 GB. Después corresponde preparar la matriz de configuraciones y avanzar al corte público/P3.


## 14. Cierre lógico L12 con dev16

La batería `AI01_BENCHMARK_20260915T174028Z.zip` repite las mismas dos páginas EXP-01 1.1 reales bajo
perfil L12 con dev16. Resultado: **3/3 modelos completos y 2/2 targets por modelo**.

| Modelo | Estado | Tiempo total | Pico GPU | Resultado cualitativo |
|---|---:|---:|---:|---|
| MiniCPM-V 4.6 Q4_K_M | 2/2 | 7,26 s | 1.704 MiB | Muy liviano, pero la salida es genérica y atribuye rasgos como sellos/firmas sin evidencia clara. |
| Gemma 4 E4B Q4_0 | 2/2 | 13,79 s | 4.876 MiB | Rápido, pero conserva el error estructural de describir el recorte periodístico de dos columnas como columna única. |
| **Qwen3.5 9B Q4_K_M** | **2/2** | **39,26 s** | **6.984 MiB** | **Mejor cobertura visual/documental:** reconoce recorte, dos columnas, manuscritos, superposición y estructura del informe. |

### Decisión L12

- **Default lógico L12:** `unsloth/Qwen3.5-9B-GGUF:Q4_K_M`.
- **Fallback rápido:** `ggml-org/gemma-4-E4B-it-GGUF:Q4_0`.
- **Baseline técnico:** `ggml-org/MiniCPM-V-4.6-GGUF:Q4_K_M`.

Qwen3.5 necesitó una expansión 512→1024 mediante `compact_retry` en el segundo target y sobreinterpretó
alguna marca como sello/tachadura. Esas limitaciones no se ocultan; quedan en la evidencia. Aun así,
la diferencia estructural respecto de E4B y MiniCPM justifica cambiar la preferencia provisional.

El pico real observado de Qwen3.5 fue ~6,98 GiB sobre RTX 3090, por lo que la selección entra holgadamente
en un presupuesto lógico de 12 GB. Esto **no sustituye la prueba en hardware físico de 12 GB**, que permanece
como gate separado.

### Evidencia pública L12

Se agrega `benchmarks/vision-describe-l12-20260915/` con las mismas capturas, request, métricas y salidas
completas. El paquete público combinado puede incluir H24 y L12 sin depender del nombre definitivo del repo.

### Próximo gate

La selección lógica P2 queda cerrada para H24 y L12. El único gate de hardware pendiente es validar L12
en una GPU física de 12 GB cuando esté disponible. Mientras tanto puede prepararse el corte público inicial
del repositorio externo y continuar con P3 sin volver a ejecutar H24/L12 por rutina.
