"""Genera las imágenes del "antes y después" para el público: radar de Piura en seco vs. el 1-abr-2017.

Mismo encuadre, misma escala de grises y la misma metodología de detección de agua que scripts/05.
- antes.png: mediana de las pasadas descendentes de sep-dic 2016 (seco).
- despues.png: pasada del 1-abr-2017 (5 días después del desborde en la ciudad).
- despues-agua.png: la misma imagen con el agua nueva resaltada en azul.
Las usa web/antes-despues/index.html (barra deslizable) y sirven tal cual para los videos.

Lee: GEE_PROJECT del .env. Escribe: web/antes-despues/{antes,despues,despues-agua}.png
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

ENCUADRE = ee.Geometry.Rectangle([-80.95, -5.95, -80.45, -5.10])  # ciudad de Piura → Sechura
CARPETA = Path("web/antes-despues")
CARPETA.mkdir(parents=True, exist_ok=True)

s1 = (
    ee.ImageCollection("COPERNICUS/S1_GRD")
    .filterBounds(ENCUADRE)
    .filter(ee.Filter.eq("instrumentMode", "IW"))
    .filter(ee.Filter.eq("orbitProperties_pass", "DESCENDING"))
    .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
    .select("VV")
)
suavizar = lambda img: img.focal_mean(50, "circle", "meters")  # noqa: E731
antes = suavizar(s1.filterDate("2016-09-01", "2016-12-31").median())
despues = suavizar(s1.filterDate("2017-04-01", "2017-04-02").mosaic())

agua = despues.lt(-16).And(antes.subtract(despues).gt(3))
agua = agua.updateMask(agua.connectedPixelCount(25, True).gte(10)).selfMask()

gris = {"min": -25, "max": 0, "palette": ["000000", "ffffff"]}
imagenes = {
    "antes": antes.visualize(**gris),
    "despues": despues.visualize(**gris),
    "despues-agua": ee.ImageCollection([despues.visualize(**gris), agua.visualize(palette=["1f6fff"])]).mosaic(),
}
for nombre, imagen in imagenes.items():
    url = imagen.getThumbURL({"region": ENCUADRE, "dimensions": 1100, "format": "png"})
    urllib.request.urlretrieve(url, CARPETA / f"{nombre}.png")
    print(f"  {nombre}.png")
