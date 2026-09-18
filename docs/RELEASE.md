# Preparación de un release público

Este documento separa lo que debe estar cerrado antes de publicar Archive Workbench AI de la historia interna de desarrollo.

## Código y contratos

- versión del paquete definida de forma coherente en `pyproject.toml`, `archive_workbench_ai.__version__` y `CITATION.cff`;
- suite canónica completa verde con el Python de la venv;
- wheel y sdist construibles desde un checkout limpio;
- `aw-ai --version`, `capabilities` y `doctor` coherentes;
- protocolo y handoff sin cambios no versionados;
- ninguna escritura directa en la SQLite de Archive Workbench.

## Distribución

- runtime fijado con hashes y rutas por plataforma;
- instalación/inspección del runtime probada por cada plataforma que se declare soportada;
- modelos fuera del artefacto principal;
- funcionamiento offline comprobado después de instalar runtime y modelos;
- actualización del paquete sin borrar runtime ni modelos;
- estrategia de migración documentada si cambia el directorio de datos.

## Integración con Archive Workbench

El puente local por buzón compartido está implementado. Antes del primer release público que anuncie integración con la distribución administrada debe validarse con los launchers y las imágenes definitivas en las plataformas declaradas. No alcanza con que el protocolo del puente pase tests unitarios.

## Documentación pública

- README de Archive Workbench AI sin instrucciones de fases internas como recorrido principal;
- instalación por plataforma;
- privacidad y uso de red;
- modelos y requisitos de hardware con límites explícitos;
- integración AW ↔ AI;
- contratos técnicos;
- licencia, cita y terceros;
- changelog;
- README y guía de primer inicio de Archive Workbench preparados para explicar el componente opcional y la integración local;
- **página dedicada de Archive Workbench AI en el sitio público de Archive Workbench**, diferida deliberadamente hasta cerrar imágenes e integración;
- enlaces, versiones, capturas e instrucciones revisados de manera conjunta en ambos repositorios y, al final, en el sitio.

## Evidencia y derechos de reproducción

Las imágenes archivísticas de benchmarks no deben incorporarse a un repositorio o release público hasta confirmar sus condiciones de reproducción. Los informes textuales pueden conservar la metodología y los resultados sin publicar automáticamente los assets restringidos.

## Publicación y validación manual final

Cuando los gates de integración y documentación estén cerrados:

1. fijar la versión de release;
2. construir wheel y sdist desde `main` limpio;
3. generar hashes SHA-256;
4. crear tag y GitHub Release;
5. adjuntar los artefactos de distribución;
6. publicar las imágenes definitivas de Archive Workbench que formen parte del recorrido integrado;
7. completar la página de Archive Workbench AI en el sitio público de AW y revisar que el README/primer inicio preparados sigan coincidiendo con los artefactos definitivos;
8. verificar instalación limpia desde los artefactos publicados;
9. **validar manualmente el recorrido público real, usando las imágenes ya publicadas:**
   - Windows: CPU solamente;
   - Ubuntu/Linux: imagen CPU;
   - Ubuntu/Linux: imagen GPU NVIDIA;
10. comprobar que las tres validaciones llegan desde selección/autorización en AW hasta propuesta revisable devuelta por Archive Workbench AI, sin acceso del motor a SQLite ni aceptación automática;
11. verificar coherencia final entre código, imágenes, wheel/sdist, hashes, README, sitio, versiones y enlaces de descarga;
12. sólo entonces cambiar la visibilidad o el estado público del repositorio según corresponda.

La validación manual final no debe adelantarse a imágenes locales o artefactos distintos de los que se hayan publicado: su objetivo es probar exactamente la distribución que recibirá una persona usuaria.

## Candidata integrada de Archive Workbench 1.3.0-rc1

La primera candidata de imágenes que incorpora el puente administrado se identifica como `1.3.0-rc1-cpu` y `1.3.0-rc1-gpu`. Su publicación no convierte todavía a 1.3.0 en versión estable ni modifica `releases/latest`.

El workflow de contenedores debe ejecutarse manualmente desde el commit de la rama candidata y conservar, además del tag, el digest inmutable de cada imagen como artefacto de GitHub Actions. Las validaciones manuales finales deben realizarse sobre esos mismos tags/digests publicados: Windows CPU, Ubuntu CPU y Ubuntu GPU NVIDIA. El sitio público de Archive Workbench se actualiza después de que esas validaciones queden verdes.

## Gate de recorrido sin terminal

Antes del primer release administrado, la ruta normal debe completarse sin terminal, activación de venv, `PATH`, variables de entorno ni rutas manuales. Los artefactos descargables deben probar instalación/preparación, apertura, análisis, propuesta pendiente, actualización/reparación y cierre. La matriz final obligatoria es Windows CPU, Ubuntu CPU y Ubuntu GPU NVIDIA. El sitio público de Archive Workbench se actualiza después de cerrar estos recorridos.

## Gates de distribución nativa administrada

Antes de cualquier release público de Archive Workbench AI deben quedar verdes los workflows `build-native.yml` y `build-linux-nvidia-runtime.yml`. Los paquetes nativos deben ejecutar el smoke del binario congelado y conservar checksums. El runtime NVIDIA candidato debe construirse desde el commit fijado, registrarse por SHA-256 y luego incorporarse al catálogo en un corte posterior.

No iniciar la validación manual final desde repositorios o venvs. Esa validación se hace sólo desde los instaladores/paquetes descargables candidatos y, para Archive Workbench, desde el bundle administrado que conserva los digests publicados de las imágenes 1.3.0-rc1.

Antes de promover los instaladores a release público, registrar también el estado de firma de código. Las candidatas técnicas pueden construirse sin firma, pero no se debe describir como instalación sin fricción una app macOS sin firma/notarización ni un instalador Windows que todavía active advertencias de reputación o firma. Este gate de distribución es independiente de la funcionalidad del bridge y de la matriz manual obligatoria Windows CPU + Ubuntu CPU/GPU.
