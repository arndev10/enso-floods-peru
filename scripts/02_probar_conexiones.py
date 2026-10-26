"""Prueba mínima de las credenciales de Copernicus CDS y NASA Earthdata.

Lee: CDSAPI_URL, CDSAPI_KEY, EARTHDATA_USERNAME, EARTHDATA_PASSWORD del .env.
Escribe: datos/prueba/era5_prueba.nc (unos KB: lluvia de 1 hora sobre Piura).
Nunca imprime los valores de las claves.
"""
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# --- Copernicus CDS ---
for variable in ("CDSAPI_URL", "CDSAPI_KEY"):
    if not os.environ.get(variable):
        raise SystemExit(f"Falta {variable} en el .env")

import cdsapi  # noqa: E402  (después de cargar el .env)

salida = Path("datos/prueba/era5_prueba.nc")
salida.parent.mkdir(parents=True, exist_ok=True)
try:
    cdsapi.Client(quiet=True, progress=False).retrieve(
        "reanalysis-era5-single-levels",
        {
            "product_type": ["reanalysis"],
            "variable": ["total_precipitation"],
            "year": ["2017"],
            "month": ["03"],
            "day": ["27"],
            "time": ["18:00"],
            "area": [-4.9, -80.9, -5.4, -80.4],  # norte, oeste, sur, este (Piura)
            "data_format": "netcdf",
        },
        str(salida),
    )
    print(f"CDS        OK  ({salida.stat().st_size / 1024:.0f} KB descargados en {salida})")
except Exception as error:  # noqa: BLE001
    print(f"CDS        FALLÓ  {type(error).__name__}: {str(error)[:300]}")

# --- NASA Earthdata ---
usuario = os.environ.get("EARTHDATA_USERNAME")
clave = os.environ.get("EARTHDATA_PASSWORD")
if not usuario or not clave:
    print("Earthdata  FALTA usuario o contraseña en el .env")
else:
    respuesta = requests.get(
        "https://urs.earthdata.nasa.gov/api/users/tokens", auth=(usuario, clave), timeout=30
    )
    if respuesta.ok:
        print("Earthdata  OK  (usuario y contraseña aceptados)")
    else:
        print(f"Earthdata  FALLÓ  HTTP {respuesta.status_code}")
