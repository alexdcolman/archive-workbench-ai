# Componentes de terceros

Archive Workbench AI coordina componentes externos que conservan sus propias licencias y condiciones de uso.

## llama.cpp

El backend de inferencia local es `llama.cpp`, desarrollado por ggml-org. Archive Workbench AI fija una revisión conocida y puede descargar binarios publicados por ese proyecto o, en Linux con NVIDIA, compilar esa revisión desde fuente. `llama.cpp` no se relicencia como parte de Archive Workbench AI.

- Proyecto: <https://github.com/ggml-org/llama.cpp>
- Release fijada por el corte actual: `b10903`, commit `481c65f091f74c5e7089dd0a3a1cc6b50cced31e`.

## GNU OpenMP runtime (`libgomp`)

El runtime administrado Linux x86_64/NVIDIA incluye `libgomp.so.1` para conservar el soporte OpenMP de `llama.cpp` sin exigir una instalación adicional en el sistema anfitrión. `libgomp` forma parte de GCC y conserva sus propios términos de licencia, incluida la GCC Runtime Library Exception aplicable. El tar del runtime incluye una copia del aviso de copyright/licencia del paquete `libgomp1` usado para construirlo.

- Proyecto: <https://gcc.gnu.org/>
- Componente: GNU Offloading and Multi Processing Runtime Library (`libgomp`).

## Modelos

Los pesos de modelos no forman parte del repositorio, del wheel ni del ZIP de Archive Workbench AI. `aw-ai models pull` descarga únicamente el modelo solicitado y verifica los hashes conocidos por el catálogo del proyecto. Cada modelo queda sujeto a los términos publicados por su proveedor o repositorio de origen.

El catálogo actual incluye familias MiniCPM-V, Gemma y Qwen. Las URL de origen se registran en `src/archive_workbench_ai/catalog.py` y también aparecen en los informes generados por el programa.

## Dependencias Python

Las dependencias Python, entre ellas Pillow, conservan sus propias licencias. La inclusión como dependencia no implica una modificación de esos términos.
