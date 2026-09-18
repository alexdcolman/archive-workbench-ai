# Modelos y hardware

Archive Workbench AI mantiene un catálogo explícito de modelos. Los pesos se descargan por separado y no forman parte del repositorio ni del wheel.

## Perfiles

### H24

Modelo por defecto: `ggml-org/gemma-4-26B-A4B-it-GGUF:Q4_0`.

La selección se cerró sobre una RTX 3090 de 24 GB utilizando material documental EXP-01 1.1. En esa batería, Gemma 26B ofreció el mejor equilibrio entre fidelidad estructural/documental, tiempo y margen de memoria.

Qwen3.6 35B-A3B permanece como referencia de mayor detalle y mayor coste. Gemma 4 E4B permanece como fallback liviano.

### L12

Modelo por defecto lógico: `unsloth/Qwen3.5-9B-GGUF:Q4_K_M`.

La selección lógica se cerró por calidad documental y el consumo observado quedó dentro del presupuesto esperado. Sin embargo, todavía falta el gate sobre una GPU física de 12 GB. Por eso el perfil no debe presentarse como físicamente validado en cualquier placa de 12 GB.

Gemma 4 E4B permanece como fallback rápido y MiniCPM-V 4.6 como baseline técnico.

## Qué se evalúa

`vision_describe/0.1` prioriza rasgos visuales y documentales que complementan el texto ya disponible:

- organización material y jerarquía visual;
- columnas y bloques;
- sellos, firmas y manuscritos;
- casillas, marcas y superposiciones;
- deterioro y calidad de copia;
- relaciones espaciales entre texto e imagen;
- incertidumbres realmente justificadas.

No se premia la retranscripción exhaustiva de texto que EXP-01 ya aporta como contexto canónico.

## Reproducibilidad

Las comparaciones históricas completas se conservan en [`docs/history/`](history/). Las imágenes archivísticas utilizadas para determinados mini-benchmarks no se publican automáticamente: su incorporación a un release requiere confirmar antes las condiciones de reproducción correspondientes.

## Seleccionar un modelo explícito

El flujo normal usa el default del perfil. Para una corrida técnica puede fijarse otro modelo del catálogo:

```bash
aw-ai analyze \
  --input EXP01.zip \
  --profile H24 \
  --model 'ggml-org/Qwen3.6-35B-A3B-GGUF:Q4_K_M'
```

La selección explícita no elimina los límites físicos del equipo ni convierte una configuración no validada en soportada.
