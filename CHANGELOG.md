# Cambios respecto del notebook base

La versión de referencia está en `reference/gaia_anguita_original.ipynb` y se conserva sin modificaciones. Esta lista identifica los cambios de la adaptación.

- Organización del análisis en funciones, notebook explicado y script de ejecución.
- Recuperación de observaciones para las fuentes FPR preseleccionadas alrededor del catálogo, con consultas y metadatos de procedencia. H1413+117 se utiliza como ejemplo explicado.
- Conservación de los identificadores largos de Gaia como texto.
- Asociación angular sobre la esfera y control del cruce de RA por 0/360 grados.
- Agrupamiento separado por lente y `source_id`, respetando el ámbito de `component_id`.
- Inicialización `k-means++`, 20 inicializaciones y semilla reproducible.
- Orden de centros por RA descendente: C1 corresponde al grupo más oriental. En el código base, el comentario describía este orden, pero la implementación ordenaba por RA ascendente.
- Registro de fallos y diagnósticos en lugar de sustituir un ajuste fallido por etiquetas originales.
- Revisión de silueta y concordancia entre diez semillas.
- Correspondencia explícita entre identificadores originales y grupos espaciales.
- Comparación temporal mediante vecinos mutuos uno a uno; se conservan las dos épocas y los identificadores. Se evita la agregación silenciosa con `first`.
- Etiquetas de tiempo y magnitud según el modelo de datos de Gaia; título correspondiente al sistema realmente seleccionado.
- Curvas con puntos, sin interpolación visual de intervalos no observados ni barras de error inferidas.
- Bibliografía, atribución del notebook de partida y explicación del alcance físico.

Los cambios anteriores mejoran la trazabilidad del procesamiento. Su validez como identificación física de imágenes o medición de microlensing requiere un análisis adicional.
