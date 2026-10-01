"""Agrupamiento espacial y comparación descriptiva de observaciones Gaia FPR."""
from itertools import combinations
from pathlib import Path
import json
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from threadpoolctl import threadpool_limits

PARAMETROS = {
    "radio_arcsec": 3.0,
    "semilla": 42,
    "n_init": 20,
    "semillas_estabilidad": list(range(10)),
    "muestra_silueta": 1000,
    "tolerancia_segundos": 1.0,
}
CLAVE_OBSERVACION = ["solution_id", "source_id", "component_id", "observation_id"]


def cargar_datos(carpeta):
    carpeta = Path(carpeta)
    catalogo = pd.read_csv(carpeta / "lenses.csv")
    observaciones = pd.read_csv(
        carpeta / "gaia_lens_observations.csv",
        dtype={"solution_id": "string", "source_id": "string"},
    )
    if catalogo["name"].duplicated().any():
        raise ValueError("El catálogo contiene nombres repetidos.")
    if not np.isfinite(catalogo[["ra", "dec"]].to_numpy()).all():
        raise ValueError("El catálogo contiene coordenadas sin definir.")
    if not catalogo["ra"].between(0, 360, inclusive="left").all():
        raise ValueError("Las ascensiones rectas del catálogo deben estar en [0, 360).")
    if not catalogo["dec"].between(-90, 90).all():
        raise ValueError("Las declinaciones del catálogo deben estar en [-90, 90].")
    if observaciones[CLAVE_OBSERVACION].isna().any().any():
        raise ValueError("Hay identificadores de observación sin definir.")
    return catalogo, observaciones


def vectores_unitarios(ra, dec):
    ra, dec = np.radians(ra), np.radians(dec)
    return np.column_stack((np.cos(dec) * np.cos(ra),
                            np.cos(dec) * np.sin(ra), np.sin(dec)))


def asociar_catalogo(observaciones, catalogo, radio_arcsec=3.0):
    """Vecino más cercano en la esfera; conserva las asociaciones ambiguas."""
    datos = observaciones.copy()
    coordenadas = datos[["ra_obs", "dec_obs", "epoch_obs"]].to_numpy()
    validas = np.isfinite(coordenadas).all(axis=1)
    validas &= datos["ra_obs"].between(0, 360, inclusive="left")
    validas &= datos["dec_obs"].between(-90, 90)
    excluidas = datos.loc[~validas].copy()
    excluidas["motivo"] = "Coordenadas o época no válidas"
    datos = datos.loc[validas].copy()
    if datos.empty:
        raise ValueError("No hay observaciones con coordenadas y épocas válidas.")
    arbol = cKDTree(vectores_unitarios(catalogo["ra"], catalogo["dec"]))
    n_vecinos = min(2, len(catalogo))
    distancia, indice = arbol.query(
        vectores_unitarios(datos["ra_obs"], datos["dec_obs"]), k=n_vecinos
    )
    if n_vecinos == 1:
        distancia, indice = distancia[:, None], indice[:, None]
    # La cuerda de la esfera unitaria permite calcular la separación exacta.
    separacion = np.degrees(2 * np.arcsin(np.clip(distancia / 2, 0, 1))) * 3600
    datos["separation_arcsec"] = separacion[:, 0]
    datos["asociacion_ambigua"] = (separacion[:, 1] <= radio_arcsec
                                  if n_vecinos > 1 else False)
    for columna in catalogo:
        datos[f"lens_{columna}"] = catalogo[columna].to_numpy()[indice[:, 0]]
    dentro = datos["separation_arcsec"] <= radio_arcsec
    fuera = datos.loc[~dentro].copy()
    fuera["motivo"] = "Fuera del radio de asociación"
    excluidas = pd.concat([excluidas, fuera], ignore_index=True)
    datos = datos.loc[dentro].copy()
    # El ajuste de RA evita discontinuidades al cruzar 0/360 grados.
    delta_ra = (datos["ra_obs"] - datos["lens_ra"] + 180) % 360 - 180
    datos["dra_arcsec"] = delta_ra * np.cos(np.radians(datos["lens_dec"])) * 3600
    datos["ddec_arcsec"] = (datos["dec_obs"] - datos["lens_dec"]) * 3600
    return datos.reset_index(drop=True), excluidas


def agrupar_posiciones(puntos, k, semilla=42, n_init=20):
    """C1 es el centro de mayor RA; los números no son etiquetas físicas A/B."""
    puntos = np.asarray(puntos, dtype=float)
    if not np.isfinite(puntos).all():
        raise ValueError("K-means requiere posiciones finitas.")
    if k < 1 or len(np.unique(puntos, axis=0)) < k:
        raise ValueError("No hay suficientes posiciones distintas para el k solicitado.")
    with threadpool_limits(limits=1):
        modelo = KMeans(n_clusters=k, init="k-means++", n_init=n_init,
                        random_state=semilla, max_iter=500).fit(puntos)
    if len(np.unique(modelo.labels_)) != k:
        raise ValueError("El ajuste produjo un grupo vacío.")
    centros = modelo.cluster_centers_
    orden = np.lexsort((-centros[:, 1], -centros[:, 0]))
    mapa = np.empty(k, dtype=int)
    mapa[orden] = np.arange(1, k + 1)
    return mapa[modelo.labels_], centros[orden], float(modelo.inertia_)


def analizar_componentes(datos, parametros=None):
    configuracion = {**PARAMETROS, **(parametros or {})}
    resultado = datos.copy()
    resultado["spatial_component_id"] = pd.Series(pd.NA, index=resultado.index,
                                                  dtype="Int64")
    resultado["cluster_status"] = "pendiente"
    diagnosticos, centros_todos, estabilidad, correspondencias = [], [], [], []
    # component_id solo es único dentro de cada source_id de Gaia.
    for (nombre, fuente), grupo in resultado.groupby(["lens_name", "source_id"], sort=True):
        puntos = grupo[["dra_arcsec", "ddec_arcsec"]].to_numpy()
        k = grupo["component_id"].nunique()
        base = {"lens_name": nombre, "source_id": fuente,
                "observaciones": len(grupo), "k_gaia": int(k),
                "n_img_catalogo": grupo["lens_n_img"].iloc[0],
                "fuentes_gaia_en_lente": datos.loc[datos["lens_name"].eq(nombre),
                                                   "source_id"].nunique(),
                "asociacion_ambigua": bool(grupo["asociacion_ambigua"].any())}
        try:
            etiquetas, centros, inercia = agrupar_posiciones(
                puntos, k, configuracion["semilla"], configuracion["n_init"]
            )
        except ValueError as error:
            resultado.loc[grupo.index, "cluster_status"] = "fallido"
            diagnosticos.append({**base, "estado": "fallido", "detalle": str(error)})
            continue
        resultado.loc[grupo.index, "spatial_component_id"] = etiquetas
        resultado.loc[grupo.index, "cluster_status"] = "ok"
        silueta = np.nan
        if 1 < k < len(grupo):
            # La muestra conserva al menos una posición de cada grupo.
            muestra = np.arange(len(grupo))
            if len(muestra) > configuracion["muestra_silueta"]:
                rng = np.random.default_rng(configuracion["semilla"])
                necesarias = np.array([rng.choice(np.flatnonzero(etiquetas == c))
                                       for c in np.unique(etiquetas)])
                resto = np.setdiff1d(muestra, necesarias)
                cantidad = max(0, configuracion["muestra_silueta"] - k)
                muestra = np.concatenate([necesarias, rng.choice(resto, cantidad, replace=False)])
            with threadpool_limits(limits=1):
                silueta = float(silhouette_score(puntos[muestra], etiquetas[muestra]))
        ari = []
        for semilla in configuracion["semillas_estabilidad"]:
            otras, _, otra_inercia = agrupar_posiciones(
                puntos, k, semilla, configuracion["n_init"]
            )
            valor = float(adjusted_rand_score(etiquetas, otras))
            ari.append(valor)
            estabilidad.append({"lens_name": nombre, "source_id": fuente,
                                "semilla": semilla, "inercia_arcsec2": otra_inercia,
                                "ARI": valor})
        diagnosticos.append({**base, "estado": "ok", "detalle": "",
                             "inercia_arcsec2": inercia, "silueta": silueta,
                             "ARI_minimo": min(ari), "ARI_medio": np.mean(ari)})
        for i, centro in enumerate(centros, 1):
            seleccion = grupo.loc[etiquetas == i]
            centros_todos.append({"lens_name": nombre, "source_id": fuente,
                                 "spatial_component_id": i,
                                 "dra_arcsec": centro[0], "ddec_arcsec": centro[1],
                                 "observaciones": len(seleccion),
                                 "magnitudes_validas": int(np.isfinite(seleccion["g_mag_obs"]).sum()),
                                 "g_mediana": seleccion["g_mag_obs"].median()})
        tabla = pd.DataFrame({"original": grupo["component_id"].to_numpy(),
                              "espacial": etiquetas}).value_counts().reset_index(name="observaciones")
        for fila in tabla.itertuples(index=False):
            correspondencias.append({"lens_name": nombre, "source_id": fuente,
                                      "gaia_component_id": fila.original,
                                      "spatial_component_id": fila.espacial,
                                      "observaciones": fila.observaciones})
    return (resultado, pd.DataFrame(diagnosticos), pd.DataFrame(centros_todos),
            pd.DataFrame(estabilidad), pd.DataFrame(correspondencias))


def indices_pareados(tiempos_a, tiempos_b, tolerancia_segundos=1.0):
    """Vecinos temporales mutuos y uno a uno, sin interpolación."""
    a, b = np.asarray(tiempos_a, dtype=float), np.asarray(tiempos_b, dtype=float)
    if len(a) == 0 or len(b) == 0:
        return np.array([], dtype=int), np.array([], dtype=int)
    if tolerancia_segundos < 0 or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("La tolerancia debe ser positiva y las épocas finitas.")
    if np.any(np.diff(a) < 0) or np.any(np.diff(b) < 0):
        raise ValueError("Ordena las épocas antes de emparejarlas.")
    def mas_cercano(origen, destino):
        derecha = np.searchsorted(destino, origen)
        izquierda = np.clip(derecha - 1, 0, len(destino) - 1)
        derecha = np.clip(derecha, 0, len(destino) - 1)
        elegir_derecha = np.abs(destino[derecha] - origen) < np.abs(destino[izquierda] - origen)
        return np.where(elegir_derecha, derecha, izquierda)
    vecino_b = mas_cercano(a, b)
    vecino_a = mas_cercano(b, a)
    ia = np.arange(len(a))
    dentro = np.abs(b[vecino_b] - a) * 86400 <= tolerancia_segundos
    mutuos = vecino_a[vecino_b] == ia
    return ia[dentro & mutuos], vecino_b[dentro & mutuos]


def construir_pares(datos, tolerancia_segundos=1.0):
    registros, resumen = [], []
    validos = datos.loc[datos["cluster_status"].eq("ok") &
                       ~datos["asociacion_ambigua"] &
                       np.isfinite(datos["g_mag_obs"])].copy()
    for (nombre, fuente), grupo in validos.groupby(["lens_name", "source_id"], sort=True):
        for c1, c2 in combinations(sorted(grupo["spatial_component_id"].unique()), 2):
            a = grupo.loc[grupo["spatial_component_id"].eq(c1)].sort_values(
                ["epoch_obs", "component_id", "observation_id"]
            ).reset_index(drop=True)
            b = grupo.loc[grupo["spatial_component_id"].eq(c2)].sort_values(
                ["epoch_obs", "component_id", "observation_id"]
            ).reset_index(drop=True)
            ia, ib = indices_pareados(a["epoch_obs"], b["epoch_obs"], tolerancia_segundos)
            resumen.append({"lens_name": nombre, "source_id": fuente,
                            "componente_a": int(c1), "componente_b": int(c2),
                            "observaciones_a": len(a), "observaciones_b": len(b),
                            "pares": len(ia), "sin_par_a": len(a) - len(ia),
                            "sin_par_b": len(b) - len(ib),
                            "tolerancia_segundos": tolerancia_segundos})
            for i, j in zip(ia, ib):
                fila_a, fila_b = a.iloc[i], b.iloc[j]
                registros.append({"lens_name": nombre, "source_id": fuente,
                                  "componente_a": int(c1), "componente_b": int(c2),
                                  "gaia_component_id_a": int(fila_a["component_id"]),
                                  "gaia_component_id_b": int(fila_b["component_id"]),
                                  "observation_id_a": int(fila_a["observation_id"]),
                                  "observation_id_b": int(fila_b["observation_id"]),
                                  "epoch_a": fila_a["epoch_obs"], "epoch_b": fila_b["epoch_obs"],
                                  "epoch_media": (fila_a["epoch_obs"] + fila_b["epoch_obs"]) / 2,
                                  "delta_t_segundos": abs(fila_a["epoch_obs"] - fila_b["epoch_obs"]) * 86400,
                                  "g_a": fila_a["g_mag_obs"], "g_b": fila_b["g_mag_obs"],
                                  "delta_g": fila_a["g_mag_obs"] - fila_b["g_mag_obs"],
                                  "separacion_arcsec": np.hypot(fila_a["dra_arcsec"] - fila_b["dra_arcsec"],
                                                               fila_a["ddec_arcsec"] - fila_b["ddec_arcsec"])})
    columnas = ["lens_name", "source_id", "componente_a", "componente_b",
                "gaia_component_id_a", "gaia_component_id_b", "observation_id_a",
                "observation_id_b", "epoch_a", "epoch_b", "epoch_media", "delta_t_segundos",
                "g_a", "g_b", "delta_g", "separacion_arcsec"]
    return pd.DataFrame(registros, columns=columnas), pd.DataFrame(resumen)


def estilo_figuras():
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "figure.facecolor": "white",
                         "savefig.facecolor": "white"})


def figura_sistema(nombre, fuente, datos, centros):
    estilo_figuras()
    grupo = datos.loc[datos["lens_name"].eq(nombre) & datos["source_id"].eq(fuente) &
                      datos["cluster_status"].eq("ok")]
    if grupo.empty:
        raise ValueError("El sistema solicitado no tiene un ajuste válido.")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.7), constrained_layout=True)
    colores = plt.get_cmap("tab10")
    for componente, filas in grupo.groupby("spatial_component_id"):
        color = colores((int(componente) - 1) % 10)
        filas = filas.sort_values("epoch_obs")
        etiqueta = f"C{componente} (n={len(filas)})"
        ax1.scatter(filas["epoch_obs"], filas["g_mag_obs"], s=18, color=color,
                    alpha=0.75, label=etiqueta)
        ax2.scatter(filas["dra_arcsec"], filas["ddec_arcsec"], s=13,
                    color=color, alpha=0.55, label=f"C{componente}")
        centro = centros.loc[centros["lens_name"].eq(nombre) & centros["source_id"].eq(fuente) &
                             centros["spatial_component_id"].eq(componente)].iloc[0]
        ax2.scatter(centro["dra_arcsec"], centro["ddec_arcsec"], marker="x", s=100,
                    color=color, linewidths=2)
    ax1.set(title="Onboard G-band light curves", xlabel="BJD (TCB) - 2455197.5 [days]",
            ylabel="Onboard G magnitude [mag]")
    ax1.invert_yaxis()
    ax1.legend(fontsize=8, frameon=False)
    ax2.set(title="Spatial groups and centroids", xlabel="RA offset × cos(Dec) [arcsec]",
            ylabel="Dec offset [arcsec]")
    ax2.invert_xaxis()
    ax2.set_aspect("equal", adjustable="datalim")
    ax2.legend(fontsize=8, frameon=False)
    for ax in (ax1, ax2):
        ax.grid(alpha=0.2)
    fig.suptitle(f"{nombre} | Gaia source_id {fuente}", fontsize=12)
    return fig


def figura_diferencias(nombre, fuente, pares, tolerancia_segundos=1.0):
    estilo_figuras()
    grupo = pares.loc[pares["lens_name"].eq(nombre) & pares["source_id"].eq(fuente)]
    if grupo.empty:
        raise ValueError("El sistema solicitado no tiene observaciones emparejadas.")
    fig, ax = plt.subplots(figsize=(10, 4.7), constrained_layout=True)
    for (a, b), filas in grupo.groupby(["componente_a", "componente_b"]):
        ax.scatter(filas["epoch_media"], filas["delta_g"], s=23, alpha=0.8,
                   label=f"C{a} − C{b} (n={len(filas)})")
    ax.set(title=f"{nombre} | Raw component magnitude differences",
           xlabel="BJD (TCB) - 2455197.5 [days]", ylabel="ΔG = G(A) − G(B) [mag]")
    ax.grid(alpha=0.2)
    fig.legend(loc="outside upper center", ncol=3, frameon=False, fontsize=8)
    fig.text(0.5, -0.02, f"Matched within {tolerancia_segundos:g} s; no lens time-delay correction",
             ha="center", fontsize=9, color="#555555")
    return fig


def ejecutar_proyecto(raiz, parametros=None, ejemplos=("H1413+117", "J0203+1612", "J0248+1913")):
    raiz = Path(raiz)
    configuracion = {**PARAMETROS, **(parametros or {})}
    catalogo, originales = cargar_datos(raiz / "data/raw")
    repetidas = int(originales.duplicated().sum())
    unicas = originales.drop_duplicates().copy()
    if unicas.duplicated(CLAVE_OBSERVACION).any():
        raise ValueError("La misma clave Gaia tiene contenidos distintos; revisar antes de continuar.")
    asociadas, excluidas = asociar_catalogo(unicas, catalogo, configuracion["radio_arcsec"])
    datos, diagnosticos, centros, estabilidad, correspondencias = analizar_componentes(asociadas, configuracion)
    pares, resumen_pares = construir_pares(datos, configuracion["tolerancia_segundos"])
    return exportar_resultados(raiz, catalogo, originales, datos, excluidas, diagnosticos,
                               centros, estabilidad, correspondencias, pares, resumen_pares,
                               configuracion, ejemplos)


def exportar_resultados(raiz, catalogo, originales, datos, excluidas, diagnosticos,
                       centros, estabilidad, correspondencias, pares, resumen_pares,
                       parametros=None, ejemplos=("H1413+117", "J0203+1612", "J0248+1913")):
    """Guarda tablas ya calculadas sin repetir el ajuste de K-means."""
    raiz = Path(raiz)
    configuracion = {**PARAMETROS, **(parametros or {})}
    repetidas = int(originales.duplicated().sum())
    cobertura = catalogo[["name", "n_img"]].copy()
    conteo = datos.groupby("lens_name").agg(observaciones=("source_id", "size"),
                                           fuentes_gaia=("source_id", "nunique"))
    cobertura = cobertura.merge(conteo, left_on="name", right_index=True, how="left")
    cobertura[["observaciones", "fuentes_gaia"]] = cobertura[["observaciones", "fuentes_gaia"]].fillna(0).astype(int)
    sensibilidad = []
    for segundos in [0.1, 1.0, 10.0]:
        otros_pares, _ = construir_pares(datos, segundos)
        sensibilidad.append({"tolerancia_segundos": segundos, "pares": len(otros_pares)})
    tablas = {"observaciones_agrupadas": datos, "diagnostico_sistemas": diagnosticos,
              "centros_componentes": centros, "estabilidad_semillas": estabilidad,
              "correspondencia_componentes": correspondencias, "pares_temporales": pares,
              "resumen_pares": resumen_pares, "cobertura_catalogo": cobertura,
              "observaciones_excluidas": excluidas,
              "sensibilidad_temporal": pd.DataFrame(sensibilidad)}
    resumen = {"objetivos_catalogo": len(catalogo), "observaciones_originales": len(originales),
               "filas_exactamente_repetidas": repetidas, "observaciones_asociadas": len(datos),
               "observaciones_excluidas": len(excluidas), "lentes_con_datos": datos["lens_name"].nunique(),
               "grupos_lente_fuente": len(diagnosticos),
               "ajustes_validos": int(diagnosticos["estado"].eq("ok").sum()),
               "ajustes_fallidos": int(diagnosticos["estado"].eq("fallido").sum()),
               "componentes_espaciales": len(centros), "pares_temporales": len(pares),
               "asociaciones_ambiguas": int(datos["asociacion_ambigua"].sum()),
               "magnitudes_faltantes": int(datos["g_mag_obs"].isna().sum()),
               "parametros": configuracion}
    for carpeta in [raiz / "data/processed", raiz / "results", raiz / "figures"]:
        carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, tabla in tablas.items():
        destino = raiz / ("data/processed" if nombre in ["observaciones_agrupadas", "pares_temporales"] else "results")
        tabla.to_csv(destino / f"{nombre}.csv", index=False)
    (raiz / "results/resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False) + "\n")
    for nombre in ejemplos:
        candidatas = diagnosticos.loc[diagnosticos["lens_name"].eq(nombre) & diagnosticos["estado"].eq("ok")]
        for fila in candidatas.itertuples(index=False):
            seguro = re.sub(r"[^A-Za-z0-9_+-]", "_", nombre)
            fig = figura_sistema(nombre, fila.source_id, datos, centros)
            fig.savefig(raiz / "figures" / f"{seguro}_{fila.source_id}_components.png", dpi=170, bbox_inches="tight")
            plt.close(fig)
            if pares["lens_name"].eq(nombre).any() and pares["source_id"].eq(fila.source_id).any():
                fig = figura_diferencias(nombre, fila.source_id, pares, configuracion["tolerancia_segundos"])
                fig.savefig(raiz / "figures" / f"{seguro}_{fila.source_id}_differences.png", dpi=170, bbox_inches="tight")
                plt.close(fig)
    return resumen, tablas
