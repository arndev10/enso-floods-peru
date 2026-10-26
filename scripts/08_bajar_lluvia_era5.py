"""Baja la lluvia horaria ERA5 y ERA5-Land de enero a abril de 2017 sobre la cuenca del Piura.

Recuadro: la cuenca completa con margen (lat -4.6 a -6.0, lon -81.1 a -79.3).
Peso esperado: < 50 MB en total (rejillas de 0.25° y 0.1°).

Lee: CDSAPI_URL y CDSAPI_KEY del .env. Escribe: datos/lluvia/era5_*_2017.nc (no van a git).
"""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
import cdsapi  # noqa: E402  (después de cargar el .env)

CARPETA = Path("datos/lluvia")
CARPETA.mkdir(parents=True, exist_ok=True)
AREA = [-4.6, -81.1, -6.0, -79.3]  # norte, oeste, sur, este
cliente = cdsapi.Client(quiet=True, progress=False)

for dataset, nombre in (
    ("reanalysis-era5-single-levels", "era5"),
    ("reanalysis-era5-land", "era5land"),
):
    salida = CARPETA / f"{nombre}_2017-01a04.nc"
    peticion = {
        "variable": ["total_precipitation"],
        "year": ["2017"],
        "month": ["01", "02", "03", "04"],
        "day": [f"{d:02d}" for d in range(1, 32)],
        "time": [f"{h:02d}:00" for h in range(24)],
        "area": AREA,
        "data_format": "netcdf",
        "download_format": "unarchived",
    }
    if dataset == "reanalysis-era5-single-levels":
        peticion["product_type"] = ["reanalysis"]
    cliente.retrieve(dataset, peticion, str(salida))
    print(f"{nombre:9} → {salida} ({salida.stat().st_size / 1e6:.1f} MB)")
