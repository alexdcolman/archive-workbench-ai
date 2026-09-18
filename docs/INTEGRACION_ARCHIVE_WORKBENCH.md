# Integración con Archive Workbench

Archive Workbench AI es un componente externo. La integración está diseñada para mantener separadas la inferencia automática y las decisiones archivísticas.

## Flujo gobernado

```text
selección humana en Archive Workbench
→ autorización de uso de IA
→ generación EXP-01
→ ejecución de Archive Workbench AI
→ resultado + handoff propositivo
→ recepción en Archive Workbench
→ revisión humana
→ eventual aceptación o descarte
```

Archive Workbench AI no abre SQLite, no importa módulos internos privados de Archive Workbench y no modifica registros del proyecto.

## Entrada: EXP-01

Archive Workbench genera el paquete que delimita qué material puede analizarse. El motor procesa únicamente los assets incluidos y el contexto declarado en ese paquete.

EXP-01 1.1 puede aportar texto canónico y geometría de objetos textuales. Ese texto se trata como contexto ya disponible; la tarea visual no intenta sustituir al OCR ni reescribir de forma exhaustiva el contenido canónico.

## Salida: handoff propositivo

El resultado consolidado se convierte en `archive_workbench_ai_result_handoff/0.1`. Su política es propositiva: Archive Workbench muestra las propuestas y requiere una acción humana posterior antes de incorporarlas a la capa de revisión.

La incorporación tampoco implica aceptación automática. Revisión, historial y vigencia pertenecen a Archive Workbench.

## Ejecución directa

Cuando Archive Workbench puede acceder al ejecutable nativo:

```bash
export ARCHIVE_WORKBENCH_AI_EXECUTABLE=/ruta/a/aw-ai
```

Archive Workbench consulta las capacidades, crea el EXP-01 autorizado, ejecuta `aw-ai analyze` y recibe el handoff en la misma superficie de análisis asistido.

## Distribución administrada de Archive Workbench

La distribución pública de Archive Workbench usa Docker, mientras Archive Workbench AI se ejecuta de forma nativa para aprovechar Metal/CUDA del host. Ambos procesos se coordinan mediante un **buzón local de trabajos** ubicado dentro de `ArchiveWorkbenchData/Settings/archive-workbench-ai-bridge`.

No se abre un servidor HTTP ni se publica un puerto del host. El lanzador de Archive Workbench inicia, cuando `aw-ai` está disponible, el compañero nativo con:

```bash
aw-ai bridge start --root RUTA/ArchiveWorkbenchData/Settings/archive-workbench-ai-bridge
```

El contenedor recibe `ARCHIVE_WORKBENCH_AI_BRIDGE_DIR=/workspace/Settings/archive-workbench-ai-bridge`. Cuando una persona inicia un análisis, Archive Workbench:

1. copia al buzón únicamente el EXP-01 ya autorizado;
2. crea un request acotado con perfil, modelo, semilla y parámetros de generación;
3. identifica el trabajo con UUID y SHA-256 del input;
4. autentica el request con el secreto local generado por el compañero;
5. espera `result.zip` y `handoff.zip`;
6. verifica sus hashes antes de copiarlos a la carpeta normal de exportaciones de AW.

El request no admite rutas del host ni nombres de archivo arbitrarios. Los nombres internos del job son fijos (`input.exp01.zip`, `request.json`, `result.zip`, `handoff.zip`). El compañero procesa trabajos secuencialmente y nunca recibe una ruta a SQLite.

Comandos de administración:

```bash
aw-ai bridge init --root RUTA
aw-ai bridge start --root RUTA
aw-ai bridge status --root RUTA --json
aw-ai bridge stop --root RUTA
```

La existencia del transporte no equivale todavía a declarar cerrada la distribución pública. Debe probarse con los launchers y las imágenes definitivas en las plataformas de release.

## Cierre público conjunto

La integración no queda cerrada únicamente porque el transporte host ↔ contenedor funcione. El README y la guía de primer inicio de Archive Workbench ya quedan preparados para explicar el componente opcional y el puente local. La página dedicada a Archive Workbench AI en el sitio público de Archive Workbench se completa al final, cuando las imágenes e integración estén cerradas, para documentar exactamente el recorrido publicado.

Antes del release público conjunto también debe verificarse que ambos proyectos mantengan instrucciones coherentes sobre instalación, privacidad, perfiles/modelos y revisión humana. Después de publicar las imágenes definitivas de Archive Workbench, el recorrido integrado debe validarse manualmente con esos mismos artefactos en Windows CPU, Ubuntu CPU y Ubuntu GPU NVIDIA.

## Candidata de imágenes 1.3.0-rc1

Archive Workbench prepara una candidata `1.3.0-rc1` para validar el bridge dentro de las imágenes administradas antes de promover una versión estable. Las imágenes se publican como `1.3.0-rc1-cpu` y `1.3.0-rc1-gpu`; cada build registra su digest para que las pruebas manuales puedan identificar exactamente el artefacto evaluado.

Esta candidata no cambia los contratos EXP-01/handoff ni la frontera de seguridad: el contenedor sigue enviando únicamente el EXP-01 autorizado al buzón compartido y Archive Workbench AI continúa ejecutándose de forma nativa sin abrir SQLite.
