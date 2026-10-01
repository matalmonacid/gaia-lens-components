# Datos, atribución y procedencia

## Observaciones Gaia

La tabla `gaiafpr.lens_observation` pertenece al Gaia Focused Product Release. La entrega incluye 34.654 observaciones de 390 fuentes FPR preseleccionadas alrededor del catálogo de 340 objetivos. La preselección utiliza posiciones medias de componentes de `gaiafpr.lens_candidates` dentro de 10 arcsec; el análisis posterior selecciona observaciones individuales dentro de 3 arcsec. Hay datos seleccionados para 289 objetivos. H1413+117, fuente Gaia `1225461582386571008`, sirve como ejemplo explicado, con 143 observaciones. La copia de las observaciones conserva los identificadores originales, las épocas, las posiciones y la fotometría a bordo. El archivo `data/raw/download_metadata.json` documenta la consulta, fecha de descarga, número de filas y sumas SHA-256.

**Cita del conjunto de datos:** European Space Agency, Gaia Collaboration, Krone-Martins, A. et al. (2023), versión 1.0. DOI: [10.57780/esa-sfvnhs3](https://doi.org/10.57780/esa-sfvnhs3).

**Artículo asociado:** Gaia Collaboration, Krone-Martins, A. et al. (2024), *A&A*, 685, A130. DOI: [10.1051/0004-6361/202347273](https://doi.org/10.1051/0004-6361/202347273).

Se reconoce el trabajo de la misión Gaia de la Agencia Espacial Europea y del consorcio DPAC, financiado por las instituciones nacionales que participan en el acuerdo multilateral Gaia. Los [créditos oficiales](https://www.cosmos.esa.int/web/gaia-users/credits) detallan esta contribución.

La [ficha oficial de ESA](https://esdcdoi.esac.esa.int/doi/html/data/astronomy/gaia/FPR_EOLENS.html) indica que los datos de sus archivos científicos se distribuyen bajo [CC BY-NC 3.0 IGO](https://creativecommons.org/licenses/by-nc/3.0/igo/). Esta condición corresponde a los datos y no concede una licencia sobre el notebook base o el catálogo facilitado.

## Catálogo de objetivos

`data/raw/lenses.csv` conserva, sin modificaciones, el catálogo de 340 objetivos facilitado junto al notebook. El código original lo relaciona con SLED, pero el CSV no contiene metadatos que permitan confirmar el origen y la versión de la exportación. No se atribuye esta exportación a una publicación específica sin comprobarlo.

Las columnas del catálogo incluyen coordenadas, separación de imágenes, número de imágenes y redshifts. Algunos valores están ausentes. Los campos de número de imágenes sirven como contexto y no se utilizan para imponer el número de grupos de K-means.

## Código de partida y adaptación

Notebook base facilitado por el **Dr. Timo Anguita**, director del Doctorado en Astrofísica de la Universidad Andrés Bello, sede Santiago, de acuerdo con su [perfil institucional](https://facultades.unab.cl/cienciasexactas/academico/timo-anguita/).

**Adaptación, documentación y organización del proyecto:** Matías Almonacid Mellado.

El archivo original se conserva en `reference/`. La adaptación incorpora una ejecución reproducible, controles de datos, identificación de grupos por fuente Gaia, estabilidad entre semillas y emparejamiento temporal explícito. Este repositorio no atribuye al profesor las modificaciones añadidas ni implica su revisión o aprobación.
