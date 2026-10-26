"""Prueba mínima de Earth Engine: lista las imágenes Sentinel-1 sobre Piura en marzo de 2017.

Lee: GEE_PROJECT del .env. Escribe: nada. No descarga imágenes; solo consulta
metadatos en la nube de Google.
"""
import os
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

import ee  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv()
ee.Initialize(project=os.environ["GEE_PROJECT"])

# Recuadro aproximado de Piura–Castilla (lon/lat)
piura = ee.Geometry.Rectangle([-80.75, -5.30, -80.55, -5.10])

coleccion = (
    ee.ImageCollection("COPERNICUS/S1_GRD")
    .filterBounds(piura)
    .filterDate("2017-02-15", "2017-04-15")
    .filter(ee.Filter.eq("instrumentMode", "IW"))
    .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
)

fechas = coleccion.aggregate_array("system:time_start").getInfo()
orbitas = coleccion.aggregate_array("orbitProperties_pass").getInfo()

print(f"Imágenes Sentinel-1 sobre Piura (15-feb a 15-abr de 2017): {len(fechas)}")
for ms, orbita in sorted(zip(fechas, orbitas)):
    print(" ", ee.Date(ms).format("YYYY-MM-dd HH:mm").getInfo(), orbita)
