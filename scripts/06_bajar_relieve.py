"""Baja el relieve FABDEM (30 m, sin edificios ni árboles) del dominio de inundación desde Earth Engine.

FABDEM está en el catálogo comunitario de Earth Engine (awesome-gee-community-catalog).
Dominio: ciudad de Piura → Bajo Piura → depresión de Sechura (el agua de 2017 salió de la cuenca).

Lee: GEE_PROJECT del .env. Escribe: datos/relieve/fabdem_bajo_piura.tif (~25 MB, no va a git).
"""
import os
import urllib.request
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)

import ee  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv()
ee.Initialize(project=os.environ["GEE_PROJECT"])

DOMINIO = ee.Geometry.Rectangle([-81.0, -6.0, -80.4, -5.05])
salida = Path("datos/relieve/fabdem_bajo_piura.tif")
salida.parent.mkdir(parents=True, exist_ok=True)

fabdem = ee.ImageCollection("projects/sat-io/open-datasets/FABDEM").filterBounds(DOMINIO).mosaic()
url = fabdem.toFloat().getDownloadURL(
    {"region": DOMINIO, "scale": 30, "crs": "EPSG:32717", "format": "GEO_TIFF"}  # UTM 17S
)
urllib.request.urlretrieve(url, salida)
print(f"Relieve: {salida} ({salida.stat().st_size / 1e6:.1f} MB)")
