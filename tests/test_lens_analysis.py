"""Comprobaciones de los errores que puede introducir el procesamiento."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.lens_analysis import (agrupar_posiciones, asociar_catalogo,
                              cargar_datos, indices_pareados)


class AnalisisLentesTest(unittest.TestCase):
    def test_asociacion_cruza_cero_de_ra(self):
        catalogo = pd.DataFrame({"name": ["cero"], "ra": [359.9998], "dec": [0.0]})
        observaciones = pd.DataFrame({"ra_obs": [0.0001], "dec_obs": [0.0], "epoch_obs": [1.0]})
        datos, excluidas = asociar_catalogo(observaciones, catalogo, 3)
        self.assertTrue(excluidas.empty)
        self.assertEqual(datos.loc[0, "lens_name"], "cero")
        self.assertAlmostEqual(datos.loc[0, "dra_arcsec"], 1.08, places=6)
        self.assertAlmostEqual(datos.loc[0, "separation_arcsec"], 1.08, places=6)

    def test_asociacion_ambigua_queda_marcada(self):
        catalogo = pd.DataFrame({"name": ["a", "b"], "ra": [20.0, 20.0005], "dec": [0.0, 0.0]})
        observaciones = pd.DataFrame({"ra_obs": [20.0001], "dec_obs": [0.0], "epoch_obs": [1.0]})
        datos, _ = asociar_catalogo(observaciones, catalogo, 3)
        self.assertTrue(datos.loc[0, "asociacion_ambigua"])

    def test_c1_es_el_grupo_de_mayor_ra(self):
        puntos = np.array([[-1, 0], [-1.1, 0.1], [1, 0], [1.1, -0.1]])
        etiquetas, centros, _ = agrupar_posiciones(puntos, 2)
        self.assertGreater(centros[0, 0], centros[1, 0])
        np.testing.assert_array_equal(etiquetas, [2, 2, 1, 1])

    def test_no_disimula_un_k_imposible(self):
        with self.assertRaises(ValueError):
            agrupar_posiciones(np.array([[0, 0], [0, 0]]), 2)

    def test_emparejamiento_no_reutiliza_observaciones(self):
        dia = 1700.0
        a = dia + np.array([0.0, 0.2, 2.0]) / 86400
        b = dia + np.array([0.1, 2.5]) / 86400
        ia, ib = indices_pareados(a, b, 1.0)
        self.assertEqual(len(ib), len(np.unique(ib)))
        self.assertEqual(len(ia), 2)
        self.assertTrue((np.abs(a[ia] - b[ib]) * 86400 <= 1).all())
        ia, ib = indices_pareados(a, b, 0.05)
        self.assertEqual(len(ia), 0)

    def test_los_identificadores_grandes_no_se_redondean(self):
        with tempfile.TemporaryDirectory() as directorio:
            carpeta = Path(directorio)
            pd.DataFrame({"name": ["lente"], "ra": [20.0], "dec": [0.0]}).to_csv(carpeta / "lenses.csv", index=False)
            identificador = "4290905085881088384"
            pd.DataFrame({"solution_id": ["999999999999999999"], "source_id": [identificador],
                          "component_id": [1], "observation_id": [1]}).to_csv(carpeta / "gaia_lens_observations.csv", index=False)
            _, observaciones = cargar_datos(carpeta)
            self.assertEqual(observaciones.loc[0, "source_id"], identificador)


if __name__ == "__main__":
    unittest.main()
