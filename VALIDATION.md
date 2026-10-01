# Validación de la entrega

Fecha: 1 de octubre de 2026.

## Ejecución

- Python 3.12; NumPy 2.3.5, pandas 2.2.3, SciPy 1.17.0, scikit-learn 1.8.0 y Matplotlib 3.10.8.
- Observaciones descargadas para las 390 fuentes FPR preseleccionadas; ninguna consulta quedó sin completar.
- `run_analysis.py` ejecutado con la copia local. Las 12 celdas de código del notebook se ejecutaron en orden en un proceso Python nuevo, guardando sus salidas.
- Se inspeccionaron las figuras para comprobar títulos, unidades, orientación y legibilidad.
- Se verificaron las sumas SHA-256 de catálogo, observaciones y consultas contra sus metadatos.
- El catálogo y el notebook de referencia coinciden, byte a byte, con los archivos facilitados.

## Resultados del conjunto

| Medida | Resultado |
| --- | ---: |
| Objetivos del catálogo | 340 |
| Observaciones descargadas | 34.654 |
| Observaciones dentro de 3 arcsec | 31.221 |
| Observaciones fuera del radio | 3.433 |
| Objetivos con observaciones seleccionadas | 289 |
| Grupos lente–fuente Gaia procesados | 379 |
| Ajustes fallidos | 0 |
| Grupos espaciales, sumados por lente–fuente | 864 |
| ARI mínimo entre diez semillas | 1.0000 |
| Pares temporales con tolerancia de 1 s | 18.886 |
| Pares con tolerancias de 0.1 / 1 / 10 s | 18.886 / 18.886 / 18.886 |

Los grupos se cuentan por fuente Gaia y no equivalen a imágenes físicas independientes. Los pares tampoco equivalen a épocas independientes: una observación puede compararse con componentes distintos. El recuento coincide entre las tres tolerancias en este conjunto; esa coincidencia no se supone para otros datos.

La cobertura corresponde a este producto, preselección y radio. Los 51 objetivos sin filas seleccionadas no se interpretan como objetivos sin datos en todos los productos de Gaia.

## Ejemplo H1413+117

143 observaciones, cuatro grupos con 36 / 37 / 36 / 34 mediciones, silueta 0.8769, ARI mínimo 1.0000 y 207 pares entre las seis parejas de componentes.

La estabilidad del algoritmo no representa una validación física de las imágenes ni una detección de microlensing.

## Comprobaciones automáticas

```bash
python -m unittest discover -s tests -v
```

Seis comprobaciones verifican: asociación al cruzar RA por cero, marcado de asociaciones ambiguas, orden oriental de C1, rechazo de un k imposible, emparejamiento sin reutilización y conservación de identificadores largos.

La descarga opcional depende de Gaia. Los resultados incluidos se reproducen con la copia local, sin repetir las consultas.
