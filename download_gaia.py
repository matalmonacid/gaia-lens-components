"""Actualiza las observaciones de las fuentes indicadas en config.json."""
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import hashlib
import json

import pandas as pd

SERVICIO = "https://gea.esac.esa.int/tap-server/tap"
COLUMNAS = ("solution_id,source_id,component_id,observation_id,epoch_obs,"
            "ra_obs,dec_obs,g_mag_obs,g_flux_obs,g_flux_obs_error")
MAX_FILAS = 30000


def descargar(raiz):
    raiz = Path(raiz)
    configuracion = json.loads((raiz / "config.json").read_text())
    fuentes = pd.read_csv(raiz / configuracion["source_ids_file"], dtype={"source_id": "string"})["source_id"].drop_duplicates().tolist()
    if not fuentes or not all(isinstance(x, str) and x.isdigit() for x in fuentes):
        raise ValueError("El archivo de fuentes debe contener identificadores Gaia completos como texto.")
    tablas, consultas = [], []
    for fuente in fuentes:
        consulta = (f"SELECT {COLUMNAS} FROM gaiafpr.lens_observation "
                    f"WHERE source_id={fuente} ORDER BY component_id,observation_id")
        consultas.append(consulta)
        cuerpo = urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                            "MAXREC": MAX_FILAS, "QUERY": consulta}).encode()
        peticion = Request(SERVICIO + "/sync", data=cuerpo,
                           headers={"User-Agent": "GaiaLensComponents/1.0"})
        with urlopen(peticion, timeout=60) as respuesta:
            contenido = respuesta.read()
        tabla = pd.read_csv(BytesIO(contenido), dtype={"source_id": "string", "solution_id": "string"})
        if not set(COLUMNAS.split(",")).issubset(tabla.columns):
            raise ValueError("Gaia no devolvió las columnas esperadas.")
        if len(tabla) >= MAX_FILAS:
            raise ValueError("La respuesta alcanzó MAXREC y puede estar truncada.")
        tablas.append(tabla)
        print("Fuente", fuente, "observaciones:", len(tabla))
    datos = pd.concat(tablas, ignore_index=True).drop_duplicates()
    datos = datos.sort_values(["source_id", "component_id", "observation_id"])
    archivo = raiz / "data/raw/gaia_lens_observations.csv"
    texto_consulta = "\n\n".join(consultas) + "\n"
    # La copia se sustituye únicamente después de completar todas las consultas.
    datos.to_csv(archivo, index=False)
    (raiz / "references/download_query.adql").write_text(texto_consulta)
    metadatos = {"table": "gaiafpr.lens_observation", "service_url": SERVICIO,
                 "dataset_doi": "10.57780/esa-sfvnhs3", "source_ids": fuentes,
                 "scope": "Sources explicitly selected in config.json",
                 "retrieved_utc": datetime.now(timezone.utc).isoformat(), "rows": len(datos),
                 "maxrec": MAX_FILAS, "radius_arcsec_analysis": configuracion["radio_arcsec"],
                 "query_sha256": hashlib.sha256(texto_consulta.encode()).hexdigest(),
                 "csv_sha256": hashlib.sha256(archivo.read_bytes()).hexdigest(),
                 "target_csv_sha256": hashlib.sha256((raiz / "data/raw/lenses.csv").read_bytes()).hexdigest()}
    (raiz / "data/raw/download_metadata.json").write_text(json.dumps(metadatos, indent=2) + "\n")
    print("Copia local actualizada. Ejecuta run_analysis.py para regenerar los resultados.")


if __name__ == "__main__":
    descargar(Path(__file__).resolve().parent)
