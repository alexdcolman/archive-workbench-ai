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
