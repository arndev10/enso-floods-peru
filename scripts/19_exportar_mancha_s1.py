"""Exporta la mancha observada de Sentinel-1 (1-abr-2017) como raster de 30 m en la rejilla del relieve FABDEM.

Misma metodología que scripts/05_mancha_sentinel1.py (detección de cambio contra la línea base
seca sep-dic 2016). Además exporta una máscara de "zona evaluable": se excluyen las áreas donde
el radar no puede juzgar si hubo agua, para no castigar al modelo por los puntos ciegos del satélite:
  - zona urbana (WorldCover 50): los edificios rebotan la señal y ocultan el agua;
  - agua permanente (JRC, ocurrencia > 50%);
  - laderas > 5° (sombras de radar).

Lee: GEE_PROJECT del .env, datos/relieve/fabdem_bajo_piura.tif (para la rejilla).
Escribe: validacion/s1_observado_30m.tif (1 = agua, 0 = seco), validacion/s1_evaluable_30m.tif (1 = evaluable)
"""
import os
import urllib.request
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)

import ee  # noqa: E402
import rasterio  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv()
ee.Initialize(project=os.environ["GEE_PROJECT"])

with rasterio.open("datos/relieve/fabdem_bajo_piura.tif") as r:
    t, ancho, alto = r.transform, r.width, r.height
REJILLA = {"crs": "EPSG:32717", "crs_transform": [t.a, 0, t.c, 0, t.e, t.f], "dimensions": f"{ancho}x{alto}",
           "format": "GEO_TIFF"}
region = ee.Geometry.Rectangle([-81.05, -6.05, -80.35, -5.0])

s1 = (
    ee.ImageCollection("COPERNICUS/S1_GRD")
    .filterBounds(region)
    .filter(ee.Filter.eq("instrumentMode", "IW"))
    .filter(ee.Filter.eq("orbitProperties_pass", "DESCENDING"))
    .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
    .select("VV")
)
suavizar = lambda img: img.focal_mean(50, "circle", "meters")  # noqa: E731
base = suavizar(s1.filterDate("2016-09-01", "2016-12-31").median())
evento = suavizar(s1.filterDate("2017-04-01", "2017-04-02").mosaic())

pendiente = ee.Terrain.slope(ee.ImageCollection("COPERNICUS/DEM/GLO30_2024_1").select("DEM").mosaic())
agua_permanente = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence").gt(50).unmask(0)
urbano = ee.ImageCollection("ESA/WorldCover/v200").first().select("Map").eq(50)

agua = evento.lt(-16).And(base.subtract(evento).gt(3))
agua = agua.updateMask(agua.connectedPixelCount(25, True).gte(10)).unmask(0)
evaluable = pendiente.lt(5).And(agua_permanente.Not()).And(urbano.Not()).And(evento.mask())

for imagen, nombre in ((agua.And(evaluable).toUint8(), "s1_observado_30m"), (evaluable.toUint8(), "s1_evaluable_30m")):
    salida = Path(f"validacion/{nombre}.tif")
    urllib.request.urlretrieve(imagen.getDownloadURL(REJILLA), salida)
    with rasterio.open(salida) as r:
        a = r.read(1)
    print(f"{nombre}: {salida.stat().st_size / 1e6:.1f} MB · {a.sum() * 0.0009:,.0f} km² marcados")
