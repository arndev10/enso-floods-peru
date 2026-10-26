"""Baja las capas de exposición del dominio de inundación desde Earth Engine (todo a 30 m, UTM 17S).

- Uso de suelo: ESA WorldCover 2021 (10 m → 30 m por vecino más cercano). Sirve para la rugosidad de SFINCS.
- Población: WorldPop 2017 (100 m, personas por píxel). Personas expuestas en la Fase 4.
- Edificaciones: Google Open Buildings v3 (la ciudad de hoy), número de edificios y m² de
  techo por celda de 30 m. La capa temporal de 2017 (0.5 m) es demasiado pesada para bajarla
  así. Las huellas vectoriales para Delft-FIAT se bajan aparte en la Fase 4.

Lee: GEE_PROJECT del .env. Escribe: datos/exposicion/*.tif (no van a git).
"""
import os
import urllib.error
import urllib.request
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)

import ee  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv()
ee.Initialize(project=os.environ["GEE_PROJECT"])

DOMINIO = ee.Geometry.Rectangle([-81.0, -6.0, -80.4, -5.05])
CARPETA = Path("datos/exposicion")
CARPETA.mkdir(parents=True, exist_ok=True)

REJILLA = ee.Projection("EPSG:32717").atScale(30)  # UTM 17S a 30 m, igual que el relieve FABDEM

# Huellas de Google Open Buildings v3 (imágenes ~2022-2023 = la ciudad de HOY), confianza ≥ 0.75.
# Se rasterizan a 30 m: banda 1 = número de edificios, banda 2 = m² de techo.
huellas = (
    ee.FeatureCollection("GOOGLE/Research/open-buildings/v3/polygons")
    .filterBounds(DOMINIO)
    .filter(ee.Filter.gte("confidence", 0.75))
    # Cada edificio se reduce a su centroide: así cae en UNA sola celda y no se cuenta dos veces
    .map(lambda f: ee.Feature(f.geometry().centroid(1), {"uno": 1, "area_in_meters": f.get("area_in_meters")}))
)
edificios_hoy = (
    huellas.reduceToImage(["uno"], ee.Reducer.sum()).rename("num_edificios")
    .addBands(huellas.reduceToImage(["area_in_meters"], ee.Reducer.sum()).rename("m2_techo"))
    .reproject(REJILLA).unmask(0).toUint16()  # enteros: caben en 16 bits y el pedido baja de 48 MB
)

# WorldPop viene en personas por celda de ~100 m. Para pasarlo a 30 m sin inflar el total:
# densidad (personas/m²) en su rejilla nativa × área de la celda de 30 m.
worldpop = ee.ImageCollection("WorldPop/GP/100m/pop").filter(ee.Filter.eq("country", "PER")).filter(
    ee.Filter.eq("year", 2017)
)
proyeccion_pop = worldpop.first().projection()
densidad = worldpop.mosaic().setDefaultProjection(proyeccion_pop).divide(
    ee.Image.pixelArea().reproject(proyeccion_pop)
)
personas_30m = densidad.multiply(ee.Image.pixelArea()).reproject(REJILLA).unmask(0).toFloat()

capas = {
    "worldcover_2021": ee.ImageCollection("ESA/WorldCover/v200").first().select("Map")
    .reproject(REJILLA).toUint8(),  # vecino más cercano: la moda (reduceResolution) excede el límite de Earth Engine
    "worldpop_2017": personas_30m,
    "edificios_hoy": edificios_hoy,
}

for nombre, imagen in capas.items():
    salida = CARPETA / f"{nombre}.tif"
    if salida.exists():
        print(f"{nombre:16} ya existe, se omite")
        continue
    url = imagen.getDownloadURL({"region": DOMINIO, "scale": 30, "crs": "EPSG:32717", "format": "GEO_TIFF"})
    try:
        urllib.request.urlretrieve(url, salida)
        print(f"{nombre:16} → {salida} ({salida.stat().st_size / 1e6:.1f} MB)")
    except urllib.error.HTTPError as error:
        print(f"{nombre:16} FALLÓ: {error.read().decode()[:400]}")

# Resumen rápido
personas = worldpop.mosaic().reduceRegion(ee.Reducer.sum(), DOMINIO, crs=proyeccion_pop, maxPixels=1e10).getInfo()
print(f"Población 2017 en el dominio (WorldPop, rejilla nativa): {list(personas.values())[0]:,.0f} personas")
print(f"Edificios en el dominio (Open Buildings v3, confianza ≥ 0.75): {huellas.size().getInfo():,}")
