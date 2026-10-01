"""Ejecuta el análisis con la copia de los datos incluida en el repositorio."""
from pathlib import Path
import json
from src.lens_analysis import ejecutar_proyecto

if __name__ == "__main__":
    raiz = Path(__file__).resolve().parent
    parametros = json.loads((raiz / "config.json").read_text())
    resumen, _ = ejecutar_proyecto(raiz, parametros)
    print(json.dumps(resumen, indent=2, ensure_ascii=False))
    print("Tablas guardadas en results/ y data/processed/; figuras en figures/.")
