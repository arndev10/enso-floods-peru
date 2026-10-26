"""Clima diario ERA5-Land (0.1°) desde Earth Engine para forzar Wflow (por defecto jul-2016 a may-2017).

Uso: pixi run python scripts/16_bajar_clima_era5land_gee.py [INICIO FIN]   (p. ej. 1997-07-01 1998-05-31)

ECMWF/ERA5_LAND/DAILY_AGGR (días UTC): temperatura a 2 m, presión en superficie, radiación
solar entrante y lluvia. Se dejan en las unidades finales que espera hydromt_wflow:
  temp °C · press_msl hPa · kin W/m² · precip mm/día.
ERA5-Land da presión en SUPERFICIE; hydromt espera presión a nivel del mar y la corrige con la
altura. Se lleva a nivel del mar con la fórmula barométrica estándar y la misma orografía
(elevación media de MERIT a 0.1°, calculada en local), así la corrección de hydromt devuelve la presión original.

Lee: GEE_PROJECT del .env.
Escribe: datos/wflow/era5land_diario_<AAAA-MM>a<AAAA-MM>.nc, datos/wflow/era5land_orografia.nc
"""
import os
import sys
import urllib.request
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)

import ee  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import rasterio  # noqa: E402
from rasterio.warp import Resampling, reproject  # noqa: E402
import xarray as xr  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv()
ee.Initialize(project=os.environ["GEE_PROJECT"])

OESTE, ESTE, SUR, NORTE = -81.3, -79.2, -6.3, -4.5
INICIO, FIN = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("2016-07-01", "2017-05-31")
DIAS = pd.date_range(INICIO, FIN, freq="D")
SUFIJO = f"{DIAS[0]:%Y-%m}a{DIAS[-1]:%Y-%m}"
CARPETA = Path("datos/wflow")
TEMPORAL = CARPETA / "crudo_era5land" / SUFIJO
TEMPORAL.mkdir(parents=True, exist_ok=True)
REJILLA = {
    "crs": "EPSG:4326",
    "crs_transform": [0.1, 0, OESTE, 0, -0.1, NORTE],
    "dimensions": f"{round((ESTE - OESTE) / 0.1)}x{round((NORTE - SUR) / 0.1)}",
    "format": "GEO_TIFF",
}
BANDAS = {
    "temperature_2m": "temp",
    "surface_pressure": "press_sup",
    "surface_solar_radiation_downwards_sum": "kin",
    "total_precipitation_sum": "precip",
}
coleccion = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR").filterDate(INICIO, (DIAS[-1] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"))


def bajar(imagen: ee.Image, salida: Path) -> None:
    if not salida.exists():
        urllib.request.urlretrieve(imagen.getDownloadURL(REJILLA), salida)


def leer(salida: Path) -> np.ndarray:
    with rasterio.open(salida) as r:
        return r.read()


# Una imagen multibanda (un día por banda) por variable
for banda, nombre in BANDAS.items():
    bajar(coleccion.select(banda).toBands().toFloat(), TEMPORAL / f"{nombre}.tif")
    print(f"  {nombre}")

with rasterio.open(TEMPORAL / "temp.tif") as r:
    transform, ancho, alto = r.transform, r.width, r.height
lon = transform.c + transform.a * (np.arange(ancho) + 0.5)
lat = transform.f + transform.e * (np.arange(alto) + 0.5)
coords = {"time": DIAS, "latitude": lat, "longitude": lon}
dims = ("time", "latitude", "longitude")

# Orografía a 0.1°: elevación media del MERIT Hydro de 90 m que ya bajó scripts/11
# (en Earth Engine pedía 14,400 píxeles por celda, por encima de su límite)
z = np.zeros((alto, ancho), dtype=np.float32)
with rasterio.open("datos/wflow/merit_hydro/elevtn.tif") as r:
    reproject(rasterio.band(r, 1), z, dst_transform=transform, dst_crs="EPSG:4326",
              resampling=Resampling.average, src_nodata=-9999.0, dst_nodata=0.0)
z = np.where(np.isfinite(z) & (z > -1000), z, 0.0)  # mar = 0 m
factor_mar = (1 - 0.0065 * z / 288.15) ** -5.255  # presión superficie → nivel del mar

clima = xr.Dataset(
    {
        "temp": (dims, leer(TEMPORAL / "temp.tif") - 273.15),  # K → °C
        "press_msl": (dims, leer(TEMPORAL / "press_sup.tif") / 100 * factor_mar),  # Pa → hPa (a nivel del mar)
        "kin": (dims, leer(TEMPORAL / "kin.tif") / 86400),  # J/m² por día → W/m²
        "precip": (dims, np.clip(leer(TEMPORAL / "precip.tif") * 1000, 0, None)),  # m → mm/día
    },
    coords=coords,
)
# Celdas de mar: ERA5-Land no tiene dato; se rellenan con la celda de tierra más cercana
clima = clima.where(clima["temp"] > -100).ffill("longitude").bfill("longitude")
clima.attrs = {"fuente": "ECMWF/ERA5_LAND/DAILY_AGGR vía Earth Engine (días UTC)"}
clima.to_netcdf(CARPETA / f"era5land_diario_{SUFIJO}.nc")

xr.Dataset({"elevtn": (("latitude", "longitude"), z)}, coords={"latitude": lat, "longitude": lon}).to_netcdf(
    CARPETA / "era5land_orografia.nc"
)
marzo = clima.sel(time=f"{DIAS[-1].year}-03")
print(f"ERA5-Land {SUFIJO} → {len(DIAS)} días. Marzo-{DIAS[-1].year} en el recuadro: lluvia media {marzo.precip.sum('time').mean().item():.0f} mm, "
      f"temperatura media {marzo.temp.mean().item():.1f} °C, radiación {marzo.kin.mean().item():.0f} W/m²")
