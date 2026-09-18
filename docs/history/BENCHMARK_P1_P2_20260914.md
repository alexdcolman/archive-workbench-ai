# AI-01 — benchmark P1/P2: evidencia, resultados y estado de evaluación

> **Documento histórico.** Conserva el estado y la evidencia de una fase previa de desarrollo. No contiene las instrucciones vigentes de instalación ni el estado actual del release. Para uso actual, consulte `../INSTALACION.md`, `../DISTRIBUCION.md` y el `README.md` del repositorio.

> Nota de nombre: **AI-01** era la denominación de desarrollo. El proyecto se denomina actualmente **Archive Workbench AI**. Los nombres de artefactos e identificadores históricos de esta evidencia se conservan sin reescribir.


**Fecha de consolidación:** 2026-09-14.  
**Plugin vigente:** `archive-workbench-ai01 0.1.0.dev13`.  
**Fase:** P2 activa. P1 cerrado técnicamente.  
**Tarea evaluada:** `vision_describe/0.1`.  
**Protocolo:** `archive-workbench-ai/0.1`.

## 1. Alcance de este documento

Este documento consolida la evidencia acumulada desde el smoke real de P1 hasta el benchmark P2 L12/H24. Su función es impedir que una conversación nueva reconstruya el estado desde mensajes sueltos o vuelva a repetir fallos ya diagnosticados.

Todavía **no cierra la selección definitiva de modelos**. Deja cerrados los hechos técnicos comprobados y separa las conclusiones provisionales de las comparaciones pendientes.

## 2. Entorno canónico de las corridas reales

- GPU: NVIDIA GeForce RTX 3090.
- VRAM total informada: 24.576 MiB.
- Driver NVIDIA: `580.173.02`.
- Plataforma: `Linux-7.0.0-30-generic-x86_64-with-glibc2.39`.
- Python: `3.12.3`.
- Runtime: `llama.cpp b10903`, commit `481c65f`.
- `llama-server --version`: `0.4.0-dev (build 1, commit 481c65f)`.
- Runtime validado por el plugin como `pinned` por coincidencia exacta de commit.
- Las inferencias `run`/`benchmark run` se ejecutan offline; el servidor efímero escucha sólo en `127.0.0.1` y usa un puerto libre.
- Los modelos se cargan secuencialmente; no se mantienen varios VLM residentes simultáneamente.

## 3. Corpus sintético común P2

Las comparaciones L12 y H24 usan el mismo EXP-01 (`sha256 e491d2128eb43aff0d0b3d3dec31ff5c0eab0f1483e84ce6c0d1920f12134b19`) y las mismas tres páginas:

1. `page:ai01-p2-bench:1`: memorando limpio, tabla de tres columnas, sello rojo y firma simulada.
2. `page:ai01-p2-bench:2`: copia degradada, ruido visual, fecha parcialmente ilegible, anotación marginal, sello circular superpuesto y número de registro.
3. `page:ai01-p2-bench:3`: ficha administrativa con campos estructurados, checkbox marcado y desmarcado, texto pequeño en dos columnas y sello de recepción.

Parámetros comunes:

- temperatura: `0.0`;
- seed: `0`;
- presupuesto solicitado: `512` tokens para P2;
- política de red: `offline_required`;
- salida: JSON restringido por schema `vision_describe/0.1`.

Los requests se diferencian sólo por `hardware_profile`: `L12` o `H24`.

## 4. P1 — estabilización del circuito real

P1 se cerró con MiniCPM-V 4.6 Q4_K_M sobre la RTX 3090. Antes del primer `status=complete` se identificaron y corrigieron fallos del plugin que no deben reabrirse:

- parser de revisión de `llama.cpp`: el `build 1` impreso por el binario no representa el tag `b10903`; la validación usa el commit fijado `481c65f`;
- descargas Hugging Face: manejo de `429`, reintentos y descarga reanudable con `.part`/HTTP Range;
- diagnósticos: cualquier material destinado a ser compartido se empaqueta automáticamente en `~/Downloads/`;
- `reasoning_content`: MiniCPM consumía el presupuesto en razonamiento interno; `vision_describe` usa `enable_thinking=false`;
- JSON estructurado: `response_format` se corrigió a `response_format.json_schema.schema`;
- truncamiento: ante `finish_reason=length` se permite una expansión automática auditada del presupuesto.

El smoke real final terminó `status=complete`. P1 se considera **cerrado técnicamente**.

## 5. Modelos evaluados y artefactos fijados

### MiniCPM-V 4.6

- ID: `ggml-org/MiniCPM-V-4.6-GGUF:Q4_K_M`.
- cuantización: Q4_K_M + mmproj Q8_0.
- modelo: 529.101.536 bytes.
- SHA-256 modelo: `b1a5aa76b5ef039c2e579272ea33d4bbed7e79b49bb3ff1efdb23316d6af5199`.
- mmproj: 727.954.528 bytes.
- SHA-256 mmproj: `3d8249cdd0e1cb699644eb021fbcc04320aad89fa5dc9234ef94db0846556581`.
- rol actual: baseline técnico/minimal.

### Gemma 4 E4B-it

- ID: `ggml-org/gemma-4-E4B-it-GGUF:Q4_0`.
- cuantización: Q4_0 + mmproj Q8_0.
- modelo: 4.590.807.392 bytes.
- SHA-256 modelo: `a555b900214b477d8880e7832e0b8925e139b0159640036b09fe472b6f2097f2`.
- mmproj: 559.874.816 bytes.
- SHA-256 mmproj: `197f49a93027f9843772bd24a6a9e0be2a32a788de5a3def330e9c585d86edd1`.
- rol actual: candidato L12 principal provisional.

### Qwen3.5-9B

- ID: `unsloth/Qwen3.5-9B-GGUF:Q4_K_M`.
- cuantización: Q4_K_M + mmproj BF16.
- modelo observado: 5.680.522.464 bytes.
- SHA-256 modelo: `03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8`.
- mmproj observado: 921.705.024 bytes.
- SHA-256 mmproj: `853698ce7aa6c7ba732478bad280240969ddf7b0fcbf93900046f63903a83383`.
- rol actual: evaluado; no preferido para `vision_describe/0.1` en L12.

### Gemma 4 26B-A4B-it

- ID: `ggml-org/gemma-4-26B-A4B-it-GGUF:Q4_0`.
- cuantización: Q4_0 + mmproj Q8_0.
- modelo observado: 14.618.145.824 bytes.
- SHA-256 modelo: `d208665ab1cd3a69f7a9a4bc59430e8448c8093d9b06334f566ac59d6d504a03`.
- mmproj observado: 806.408.320 bytes.
- SHA-256 mmproj: `cc4e855736da450bf1e162d8cccfe0ad685727d0c9e04ef7dd8d884f3121039b`.
- rol actual: candidato H24 experimental; viabilidad técnica confirmada en dev13.

### Qwen3.6-35B-A3B

- ID catalogado: `ggml-org/Qwen3.6-35B-A3B-GGUF:Q4_K_M`.
- cuantización prevista: Q4_K_M + mmproj Q8_0.
- estado: **todavía no evaluado en esta batería**.
- objetivo: siguiente candidato H24 antes de cerrar comparaciones de modelos.

## 6. Benchmark L12

### 6.1 Primera comparación — dev9, 2026-09-12

| Modelo | Estado | Tiempo total | Pico VRAM | Pico RAM | Generación media |
|---|---:|---:|---:|---:|---:|
| MiniCPM-V 4.6 Q4_K_M | complete | 6,965 s | 1.704 MiB | 1.077 MiB | 283,10 tok/s |
| Gemma 4 E4B-it Q4_0 | complete | 13,795 s | 4.398 MiB | 4.765 MiB | 118,55 tok/s |

Resultado: ambos estables; Gemma E4B mostró mayor fidelidad documental y MiniCPM quedó como opción mínima/rápida.

### 6.2 Comparación de tres modelos — dev9, 2026-09-12

| Modelo | Estado | Tiempo total | Pico VRAM | Pico RAM | Generación media |
|---|---:|---:|---:|---:|---:|
| MiniCPM-V 4.6 Q4_K_M | complete | 6,879 s | 1.704 MiB | 1.071 MiB | 284,35 tok/s |
| Gemma 4 E4B-it Q4_0 | complete | 14,251 s | 4.398 MiB | 4.765 MiB | 117,33 tok/s |
| Qwen3.5-9B Q4_K_M | complete | 31,479 s | 6.680 MiB | 5.574 MiB | 99,73 tok/s |

### 6.3 Evaluación cualitativa L12

**MiniCPM-V 4.6**

- muy rápido y de bajo consumo;
- página 2: detectó degradación, anotación y sello, pero omitió lecturas concretas que otros recuperaron (`revisar folio 3`, `MESA DE ENTRADAS`, `0042-AX`);
- página 3: produjo un error material al afirmar que `Requiere restauración` estaba incluido/marcado cuando la casilla está vacía; además introdujo residuos lingüísticos (`RECBIDO`, `accessible`, `somejas`, caracteres no pertinentes);
- conclusión: útil como baseline/minimal, no como candidato de máxima fidelidad.

**Gemma 4 E4B-it**

- página 1: transcripción/estructura fiel de encabezado, tabla, sello y firma;
- página 2: recuperó `revisar folio 3`, `MESA DE ENTRADAS` y `0042-AX`, y marcó correctamente la fecha parcial como incertidumbre;
- página 3: distinguió correctamente `Incluye anexos` marcado de `Requiere restauración` desmarcado y leyó control de acceso/clasificación;
- menor tendencia a agregar explicaciones no visibles;
- conclusión: **candidato L12 principal provisional**.

**Qwen3.5-9B**

- lectura detallada y buena cobertura textual;
- página 1: agregó inferencias innecesarias sobre autenticidad y sobre que la fecha 2026 indicaría un documento futuro/hipotético;
- página 2: leyó correctamente elementos clave, pero describió de forma confusa el carácter ilegible de la fecha;
- página 3: transcribió información pequeña pero simultáneamente afirmó que parte de ese texto no era legible;
- coste sustancialmente mayor sin mejora neta suficiente frente a E4B;
- conclusión: evaluado, **no desplaza a Gemma E4B** para esta tarea.

### 6.4 Estado L12

- Gemma E4B: candidato principal provisional.
- MiniCPM-V: baseline mínimo.
- Qwen3.5-9B: evaluado/no preferido para este vertical.
- Ninguno pasa todavía a `supported` para 12 GB físicos: la batería se ejecutó en RTX 3090 con perfil lógico L12. Falta validar límite de VRAM efectivo y, cuando sea posible, hardware físico de 12 GB.

## 7. Benchmark H24 — secuencia técnica de Gemma 4 26B-A4B

### 7.1 dev10 — primer intento

Benchmark `AI01_BENCHMARK_20260913T004809Z.zip`:

- Gemma E4B completó: 15,380 s, pico VRAM 4.506 MiB, pico RAM 4.760 MiB, ~117,35 tok/s.
- Gemma 26B cerró la conexión antes de producir salida (`Remote end closed connection without response`).
- estado global: `partial`.

### 7.2 dev11 — diagnóstico del OOM

Benchmark `AI01_BENCHMARK_20260913T021313Z.zip`:

- `llama.cpp --fit` no podía ajustar residencia porque el plugin fijaba `n_gpu_layers=999`;
- log: `failed to fit params to free device memory: n_gpu_layers already set by user to 999, abort`;
- luego `cudaMalloc failed: out of memory` al intentar asignar ~13.926 MiB de buffer CUDA;
- corrección: dejar `n_gpu_layers` sin fijar y reservar margen mediante `--fit-target`.

Este fallo está **resuelto** y no debe reabrirse.

### 7.3 dev12 — modelo carga, crash en bloque visual

Benchmark `AI01_BENCHMARK_20260914T235124Z.zip`:

- el OOM desapareció;
- modelo + mmproj cargaron y `llama-server` llegó a `model loaded`;
- crash al decodificar imagen en `libmtmd`:
  `GGML_ASSERT((cparams.causal_attn || cparams.n_ubatch >= n_tokens_all) && "non-causal attention requires n_ubatch >= n_tokens") failed`;
- diagnóstico incluido correctamente dentro del ZIP del benchmark;
- corrección: para Gemma 4 multimodal, fijar `--batch-size 2048 --ubatch-size 2048`.

Este fallo está **resuelto** y no debe reabrirse.

### 7.4 dev13 — corrida H24 completa

Benchmark `AI01_BENCHMARK_20260915T000508Z.zip`:

- estado: `complete`;
- targets completos: 3/3;
- tiempo total: **21,032 s**;
- carga del servidor/modelo: **5.551 ms**;
- pico de VRAM del proceso: **16.774 MiB**;
- pico RSS: **14.325 MiB**;
- red usada durante inferencia: `false`;
- configuración H24 efectiva:
  - `--fit on`;
  - `fit_target_mib=3072`;
  - `n_gpu_layers_policy=auto_unpinned`;
  - KV `q8_0/q8_0`;
  - Flash Attention `on`;
  - `batch_size=2048`;
  - `ubatch_size=2048`;
  - mmproj offload activo;
  - contexto solicitado 16.384, mínimo de ajuste 4.096.

Rendimiento por página:

| Target | Tiempo | Prompt | Salida | Generación | Pico VRAM |
|---|---:|---:|---:|---:|---:|
| página 1 | 4,744 s | 889 tok | 374 tok | 116,23 tok/s | 16.746 MiB |
| página 2 | 4,685 s | 889 tok | 377 tok | 115,88 tok/s | 16.764 MiB |
| página 3 | 4,898 s | 889 tok | 434 tok | 124,19 tok/s | 16.774 MiB |

### 7.5 Evaluación cualitativa inicial del 26B

La corrida dev13 muestra una salida estable y detallada:

- página 1: recupera correctamente encabezado, fecha/asunto, tabla, sello, firma y pie; sin incertidumbres espurias relevantes;
- página 2: recupera fecha parcial, anotación `revisar folio 3`, sello `MESA DE ENTRADAS` y registro `0042-AX`; como punto a revisar, infiere que la pieza "parece ser una transcripción o una descripción técnica de una copia de baja calidad", interpretación que excede lo estrictamente visible;
- página 3: distingue correctamente las casillas marcada/desmarcada, campos, clasificación, control de acceso y sello `RECIBIDO`.

**Conclusión provisional:** la viabilidad técnica H24 del 26B queda comprobada. En esta muestra pequeña no hay todavía evidencia suficiente para afirmar que su mejora cualitativa frente a E4B compense el aumento de memoria y tiempo. Esa comparación permanece abierta.

## 8. Comparación provisional E4B vs 26B-A4B

| Métrica | Gemma E4B (H24 dev10) | Gemma 26B-A4B (H24 dev13) |
|---|---:|---:|
| Estado | complete | complete |
| Tiempo total | 15,380 s | 21,032 s |
| Pico VRAM | 4.506 MiB | 16.774 MiB |
| Pico RAM | 4.760 MiB | 14.325 MiB |
| Generación media | 117,35 tok/s | 118,77 tok/s |

La velocidad de generación por token es similar. El 26B consume mucha más memoria y produce salidas más extensas; el tiempo total aumenta. La evaluación cualitativa debe continuar antes de elegir un default H24.

## 9. Estado canónico de P2 después de dev13

### Cerrado / comprobado

- P1 real: cerrado.
- protocolo 0.1 y JSON estructurado: estables para esta fase.
- diagnósticos automáticos en `~/Downloads/`: vigentes.
- benchmark secuencial con ZIP único: vigente.
- L12: comparación MiniCPM / E4B / Qwen3.5 completada.
- Gemma 26B-A4B: **viabilidad técnica H24 comprobada** con dev13.
- fallos `n_gpu_layers=999` y `ubatch=512` para Gemma 4 H24: resueltos.

### Abierto

1. descargar/verificar y evaluar `Qwen3.6-35B-A3B Q4_K_M` en H24;
2. comparar cualitativamente Qwen3.6, Gemma 26B y Gemma E4B sobre las mismas páginas;
3. decidir si hace falta un perfil explícito de offload MoE (`--cpu-moe` / `--n-cpu-moe`) o si `--fit` es suficiente;
4. ampliar el corpus con documentos archivísticos más exigentes antes de promover un ganador;
5. validar el perfil L12 bajo límite efectivo de 12 GB y, cuando sea posible, GPU física de 12 GB;
6. después de cerrar modelos/configuraciones, continuar con P3 de integración de exportación/importación en Archive Workbench;
7. AI-02 sigue posterior a la estabilización de AI-01.

## 10. Evidencia canónica incluida en el relevo AI-01

El relevo privado incluye bajo `evidence/benchmarks/`:

- `AI01_BENCHMARK_20260912T203219Z.zip` — dev9 MiniCPM vs Gemma E4B;
- `AI01_BENCHMARK_20260912T220922Z.zip` — dev9 MiniCPM vs E4B vs Qwen3.5;
- `AI01_BENCHMARK_20260913T004809Z.zip` — dev10 H24 parcial;
- `AI01_BENCHMARK_20260913T021313Z.zip` — dev11 OOM diagnosticado;
- `AI01_BENCHMARK_20260914T235124Z.zip` — dev12 carga OK / assert visual + diagnóstico embebido;
- `AI01_BENCHMARK_20260915T000508Z.zip` — dev13 H24 completo 26B;
- `Archive_Workbench_AI01_P2_BENCHMARK_JOB_20260912.zip` — corpus/request reproducible común.

Estos artefactos se conservan como evidencia. No son modelos ni dependencias del plugin.
