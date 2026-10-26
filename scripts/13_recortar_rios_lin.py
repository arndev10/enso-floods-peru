"""Recorta la red global de ríos de Lin et al. (2019) a la cuenca del Piura y borra el archivo global.

Lin et al. (2019), "Global estimates of reach-level bankfull river width" (Zenodo 3552776,
CC-BY 4.0): tramos de MERIT Hydro con ancho a cauce lleno (width_m) y caudal de 2 años (Q2).
Se renombran como en el catálogo de Deltares: width_m → rivwth, Q2 → qbankfull.

Lee: datos/wflow/crudo_lin2019/rivers_ge30m.shp (1.8 GB).
Escribe: datos/wflow/rivers_lin2019_piura.gpkg (pocos MB). Luego borra la carpeta cruda.
"""
import shutil
from pathlib import Path

import geopandas as gpd

CRUDO = Path("datos/wflow/crudo_lin2019")
SALIDA = Path("datos/wflow/rivers_lin2019_piura.gpkg")
RECUADRO = (-81.25, -6.25, -79.25, -4.5)  # oeste, sur, este, norte

rios = gpd.read_file(CRUDO / "rivers_ge30m.shp", bbox=RECUADRO)
rios = rios.rename(columns={"width_m": "rivwth", "Q2": "qbankfull"}).set_crs(4326, allow_override=True)
rios.to_file(SALIDA, driver="GPKG")
print(f"{len(rios)} tramos → {SALIDA} ({SALIDA.stat().st_size / 1e6:.1f} MB)")
print(f"  ancho (m): mediana {rios['rivwth'].median():.0f}, máx {rios['rivwth'].max():.0f}")
print(f"  Q2 (m³/s): mediana {rios['qbankfull'].median():.1f}, máx {rios['qbankfull'].max():.0f}")

shutil.rmtree(CRUDO)
print("Archivo global borrado.")
