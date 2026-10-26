"""Lluvia diaria GPM IMERG V07 (NASA, 0.1°) de jul-2016 a may-2017 sobre la cuenca del Piura, vía Earth Engine.

Segunda fuente de lluvia para Wflow: ERA5 subestima las lluvias convectivas del Niño Costero
(GloFAS, que usa ERA5, dio la mitad del pico de 2017). IMERG combina satélites de microondas
e infrarrojo calibrados con pluviómetros. Las imágenes de 30 min (mm/h) se suman por día local
de Perú (05:00 UTC a 05:00 UTC). Todo se calcula en la nube; solo baja la cuenca.

Lee: GEE_PROJECT del .env. Escribe: datos/wflow/imerg_diario_2016-07a2017-05.nc (no va a git).
"""
import os
import urllib.request
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)

import ee  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import rasterio  # noqa: E402
import xarray as xr  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv()
ee.Initialize(project=os.environ["GEE_PROJECT"])

OESTE, ESTE, SUR, NORTE = -81.3, -79.2, -6.3, -4.5  # múltiplos de 0.1° (rejilla de IMERG)
DIAS = pd.date_range("2016-07-01", "2017-05-31", freq="D")
CARPETA = Path("datos/wflow")
TEMPORAL = CARPETA / "crudo_imerg"
TEMPORAL.mkdir(parents=True, exist_ok=True)

imerg = ee.ImageCollection("NASA/GPM_L3/IMERG_V07").select("precipitation")


def lluvia_del_dia(fecha: str) -> ee.Image:
    inicio = ee.Date(fecha).advance(5, "hour")  # 00:00 hora de Perú = 05:00 UTC
    medias_horas = imerg.filterDate(inicio, inicio.advance(1, "day"))
    return medias_horas.sum().multiply(0.5).rename(fecha.replace("-", ""))  # mm/h × 0.5 h


# Por bloques de un mes (una imagen multibanda por mes) para no pasar el límite de descarga
for mes, dias_mes in pd.Series(DIAS).groupby(DIAS.to_period("M")):
    salida = TEMPORAL / f"imerg_{mes}.tif"
    if salida.exists():
        continue
    imagen = ee.Image.cat([lluvia_del_dia(d.strftime("%Y-%m-%d")) for d in dias_mes]).toFloat()
    url = imagen.getDownloadURL(
        {
            "crs": "EPSG:4326",
            "crs_transform": [0.1, 0, OESTE, 0, -0.1, NORTE],
            "dimensions": f"{round((ESTE - OESTE) / 0.1)}x{round((NORTE - SUR) / 0.1)}",
            "format": "GEO_TIFF",
        }
    )
    urllib.request.urlretrieve(url, salida)
    print(f"  {mes}: {len(dias_mes)} días")

# Unir los meses en un NetCDF con el mismo formato que era5_diario (precip en mm/día)
bloques = []
for archivo in sorted(TEMPORAL.glob("imerg_*.tif")):
    with rasterio.open(archivo) as r:
        bloques.append(r.read())
        transform, ancho, alto = r.transform, r.width, r.height
datos = np.concatenate(bloques, axis=0)
lon = transform.c + transform.a * (np.arange(ancho) + 0.5)
lat = transform.f + transform.e * (np.arange(alto) + 0.5)
precip = xr.DataArray(datos, dims=("time", "latitude", "longitude"),
                      coords={"time": DIAS, "latitude": lat, "longitude": lon}, name="precip")
precip.attrs = {"units": "mm/day", "fuente": "NASA GPM IMERG V07 vía Earth Engine, día local de Perú"}
salida = CARPETA / "imerg_diario_2016-07a2017-05.nc"
precip.to_dataset().to_netcdf(salida)

total_marzo = precip.sel(time="2017-03").sum("time").mean().item()
print(f"IMERG → {salida}  ({len(DIAS)} días). Lluvia media de marzo-2017 en el recuadro: {total_marzo:.0f} mm")
