"""Mancha de inundación observada por Sentinel-1 tras el desborde del río Piura (27-mar-2017).

Método (detección de cambio, estándar en mapeo de inundaciones con radar):
- Línea base seca: mediana de las pasadas descendentes de sep-dic de 2016.
- Evento: pasada descendente del 1-abr-2017 (5 días después del desborde en la ciudad).
- Agua nueva = retrodispersión VV del evento < -16 dB y caída > 3 dB frente a la línea base.
- Se descartan agua permanente (JRC Global Surface Water, ocurrencia > 50%) y laderas
  con pendiente > 5° (el radar confunde sombras con agua).
Todo se calcula en la nube de Earth Engine; solo se bajan estadísticas y una imagen PNG.

Lee: GEE_PROJECT del .env, geo/cuenca-piura-completa.geojson.
Escribe: validacion/s1-mancha-2017-04-01.png, validacion/s1-mancha-2017-04-01.json
"""
import json
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

cuenca = ee.Geometry(json.loads(Path("geo/cuenca-piura-completa.geojson").read_text(encoding="utf-8"))["geometry"])
bajo_piura = ee.Geometry.Rectangle([-81.0, -6.0, -80.4, -5.05])  # ciudad de Piura → Bajo Piura → depresión de Sechura

s1 = (
    ee.ImageCollection("COPERNICUS/S1_GRD")
    .filterBounds(bajo_piura)
    .filter(ee.Filter.eq("instrumentMode", "IW"))
    .filter(ee.Filter.eq("orbitProperties_pass", "DESCENDING"))
    .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
    .select("VV")
)
# Filtro de speckle simple (media focal de 50 m) para limpiar el ruido típico del radar
suavizar = lambda img: img.focal_mean(50, "circle", "meters")  # noqa: E731

base = suavizar(s1.filterDate("2016-09-01", "2016-12-31").median())
evento = suavizar(s1.filterDate("2017-04-01", "2017-04-02").mosaic())

pendiente = ee.Terrain.slope(ee.ImageCollection("COPERNICUS/DEM/GLO30_2024_1").select("DEM").mosaic())
agua_permanente = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence").gt(50).unmask(0)

inundado = (
    evento.lt(-16)
    .And(base.subtract(evento).gt(3))
    .And(pendiente.lt(5))
    .And(agua_permanente.Not())
    .selfMask()
)
# Quitar manchas sueltas de menos de ~10 píxeles (ruido)
inundado = inundado.updateMask(inundado.connectedPixelCount(25, True).gte(10))


def area_km2(region: ee.Geometry) -> float:
    m2 = inundado.multiply(ee.Image.pixelArea()).reduceRegion(
        ee.Reducer.sum(), region, scale=20, maxPixels=1e10, bestEffort=True
    ).get("VV")
    return ee.Number(m2).divide(1e6).getInfo() or 0.0


estadisticas = {
    "fecha_evento": "2017-04-01",
    "linea_base": "mediana sep-dic 2016 (descendente)",
    "area_inundada_km2_cuenca_completa": round(area_km2(cuenca), 1),
    "area_inundada_km2_recuadro_bajo_piura": round(area_km2(bajo_piura), 1),
    "umbrales": {"vv_evento_db": -16, "caida_db": 3, "pendiente_max_grados": 5, "agua_permanente_ocurrencia": 50},
}
Path("validacion").mkdir(exist_ok=True)
Path("validacion/s1-mancha-2017-04-01.json").write_text(json.dumps(estadisticas, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(estadisticas, indent=2, ensure_ascii=False))

# PNG: radar del evento en grises + mancha en azul + contorno de la cuenca en naranja
fondo = evento.visualize(min=-25, max=0, palette=["000000", "ffffff"])  # 3 bandas RGB, como las capas de encima
mancha = inundado.visualize(palette=["1f6fff"])
borde = ee.Image().byte().paint(ee.FeatureCollection([ee.Feature(cuenca)]), 1, 2).visualize(palette=["ff7a00"])
url = ee.ImageCollection([fondo, mancha, borde]).mosaic().getThumbURL(
    {"region": bajo_piura, "dimensions": 1400, "format": "png"}
)
try:
    urllib.request.urlretrieve(url, "validacion/s1-mancha-2017-04-01.png")
except urllib.error.HTTPError as error:
    raise SystemExit(f"Thumbnail falló: {error.read().decode()[:500]}")
print("Imagen: validacion/s1-mancha-2017-04-01.png")
