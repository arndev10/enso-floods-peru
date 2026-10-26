"""Mapa "la ciudad construida sobre los caminos del agua": Arequipa y sus torrenteras.

1. Relieve FABDEM 30 m (Earth Engine) de la ciudad y las faldas del Chachani y el Misti.
2. Acumulación de flujo con pyflwdir: por dónde baja naturalmente el agua.
3. Imagen Sentinel-2 en color natural (mediana sin nubes de 2025) de fondo.
4. Torrenteras y quebradas con nombre en OpenStreetMap (waterway), como control.

Caso aparte: Arequipa, febrero de 2026 (lluvias que corrieron por las torrenteras).
Lee: GEE_PROJECT del .env. Escribe: validacion/arequipa-caminos-agua.png, datos/arequipa/*.tif
"""
import json
import os
import urllib.request
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)

import ee  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pyflwdir  # noqa: E402
import rasterio  # noqa: E402
import rasterio.warp  # noqa: E402
import requests  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv()
ee.Initialize(project=os.environ["GEE_PROJECT"])

OESTE, SUR, ESTE, NORTE = -71.66, -16.50, -71.42, -16.24  # ciudad + faldas del Chachani y el Misti
CARPETA = Path("datos/arequipa")
CARPETA.mkdir(parents=True, exist_ok=True)
REJILLA = {"crs": "EPSG:32719", "region": ee.Geometry.Rectangle([OESTE, SUR, ESTE, NORTE]), "format": "GEO_TIFF"}


def bajar(imagen: ee.Image, nombre: str, escala: int) -> Path:
    ruta = CARPETA / f"{nombre}.tif"
    if not ruta.exists():
        urllib.request.urlretrieve(imagen.getDownloadURL({**REJILLA, "scale": escala}), ruta)
    return ruta


ruta_dem = bajar(ee.ImageCollection("projects/sat-io/open-datasets/FABDEM").filterBounds(REJILLA["region"])
                 .mosaic().toFloat(), "fabdem", 30)
s2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(REJILLA["region"])
      .filterDate("2025-04-01", "2025-11-30").filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 10)).median())
ruta_rgb = bajar(s2.visualize(bands=["B4", "B3", "B2"], min=200, max=2600, gamma=1.15), "sentinel2_rgb", 30)

with rasterio.open(ruta_dem) as r:
    dem = r.read(1).astype(np.float32)
    transform, extension = r.transform, rasterio.plot.plotting_extent(r) if hasattr(rasterio, "plot") else None
    limites = r.bounds
with rasterio.open(ruta_rgb) as r:
    rgb = np.moveaxis(r.read([1, 2, 3]), 0, -1)

flw = pyflwdir.from_dem(dem, nodata=-9999, transform=transform, latlon=False)
acumulado_km2 = flw.upstream_area(unit="km2")
# Cauces con ≥ 0.5 km² drenando, más gruesos cuanto más agua juntan (para que se lean en video)
from scipy import ndimage  # noqa: E402
capa = np.zeros(dem.shape + (4,), dtype=np.float32)
for minimo, grosor, alfa in ((0.5, 0, 0.55), (5, 1, 0.8), (50, 2, 1.0)):
    cauce = acumulado_km2 >= minimo
    if grosor:
        cauce = ndimage.binary_dilation(cauce, iterations=grosor)
    capa[cauce] = (0.25, 0.85, 1.0, alfa)  # celeste intenso

# Torrenteras y quebradas con nombre en OpenStreetMap
consulta = (f'[out:json][timeout:90];way["waterway"]["name"]({SUR},{OESTE},{NORTE},{ESTE});out geom;')
osm = []
for servidor in ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"):
    try:
        respuesta = requests.post(servidor, data={"data": consulta}, timeout=120,
                                  headers={"User-Agent": "enso-floods-peru (demo sin fines de lucro)"})
        respuesta.raise_for_status()
        osm = respuesta.json()["elements"]
        break
    except (requests.RequestException, ValueError):
        continue
nombres = {}
for via in osm:
    lon = [p["lon"] for p in via.get("geometry", [])]
    lat = [p["lat"] for p in via.get("geometry", [])]
    if len(lon) < 2:
        continue
    x, y = rasterio.warp.transform("EPSG:4326", "EPSG:32719", lon, lat)
    nombres.setdefault(via["tags"]["name"], []).append((x, y))
(CARPETA / "torrenteras_osm.json").write_text(json.dumps({k: len(v) for k, v in nombres.items()}, ensure_ascii=False, indent=1),
                                               encoding="utf-8")

ext = [limites.left, limites.right, limites.bottom, limites.top]
fig, eje = plt.subplots(figsize=(13, 14), facecolor="#0f1317")
eje.imshow((rgb * 0.55).astype(np.uint8), extent=ext, interpolation="bilinear")  # fondo oscurecido
eje.imshow(capa, extent=ext, interpolation="nearest")
for nombre, tramos in nombres.items():
    if not any(p in nombre.lower() for p in ("torrentera", "quebrada", "río", "rio")):
        continue
    for x, y in tramos:
        eje.plot(x, y, color="#ff9f1c", linewidth=1.6, alpha=0.9)
eje.set_xlim(ext[0], ext[1]); eje.set_ylim(ext[2], ext[3]); eje.set_axis_off()
eje.set_title("Arequipa: los caminos naturales del agua (celeste) bajo la ciudad", color="white", fontsize=17, loc="left")
fig.text(0.02, 0.012, "Celeste: cauces calculados con el relieve FABDEM (≥ 0.5 km² drenando). Naranja: torrenteras y quebradas en "
         "OpenStreetMap. Fondo: Sentinel-2 (2025).", color="#a9b0b8", fontsize=10)
fig.savefig("validacion/arequipa-caminos-agua.png", dpi=110, facecolor="#0f1317", bbox_inches="tight")
print(f"Mapa: validacion/arequipa-caminos-agua.png · {len(nombres)} cursos de agua con nombre en OSM")
print(sorted(n for n in nombres if "torrentera" in n.lower())[:15])
