"""Segunda opinión con imagen óptica: ¿las "falsas alarmas" del modelo eran agua que el radar no vio?

El radar detecta agua porque se ve oscura. Pero el agua entre cultivos o vegetación hace rebotar
la señal y se ve brillante: el método de detección de cambio no la marca. Landsat 8 (4-abr-2017,
3 días después de la pasada del radar) ve el agua directamente con el índice MNDWI
(verde vs. infrarrojo de onda corta), pero solo donde no hay nubes.

Se cruzan, en los píxeles DESPEJADOS de Landsat y dentro de la zona evaluable:
  - falsas alarmas del modelo (modelo con agua, radar sin agua) → ¿cuántas tienen agua en Landsat?
  - aciertos (modelo y radar con agua) → control: deberían verse como agua también en Landsat.

Entorno por defecto: pixi run python scripts/26_verificar_con_optico.py [modelos/sfincs-...]
Escribe: validacion/landsat_agua_2017-04-04_30m.tif, validacion/verificacion-optico-<modelo>.json
"""
import json
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
from dotenv import load_dotenv  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from util_sfincs import cota_subgrid_30m, niveles, profundidad_30m, rejilla_30m  # noqa: E402

MODELO = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("modelos/sfincs-bajo-piura-inf")
HORA_SATELITE = pd.Timestamp("2017-04-01 11:00")
SALIDA_LANDSAT = Path("validacion/landsat_agua_2017-04-04_30m.tif")

# --- Agua según Landsat 8 (0 = seco, 1 = agua, 255 = nube/sombra/sin dato) -----------------------
if not SALIDA_LANDSAT.exists():
    load_dotenv()
    ee.Initialize(project=os.environ["GEE_PROJECT"])
    transform, _, (alto, ancho), _ = rejilla_30m()
    l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_TOA").filterDate("2017-04-04", "2017-04-05").filterBounds(
        ee.Geometry.Rectangle([-81.05, -6.05, -80.35, -5.0])).mosaic()
    qa = l8.select("QA_PIXEL")
    # Bits del QA: 1 nube dilatada, 3 nube, 4 sombra de nube
    nublado = qa.bitwiseAnd(1 << 1).neq(0).Or(qa.bitwiseAnd(1 << 3).neq(0)).Or(qa.bitwiseAnd(1 << 4).neq(0))
    mndwi = l8.normalizedDifference(["B3", "B6"])
    agua = mndwi.gt(0).toUint8().where(nublado, 255).unmask(255)
    url = agua.getDownloadURL({"crs": "EPSG:32717", "crs_transform": [transform.a, 0, transform.c, 0, transform.e, transform.f],
                               "dimensions": f"{ancho}x{alto}", "format": "GEO_TIFF"})
    urllib.request.urlretrieve(url, SALIDA_LANDSAT)

with rasterio.open(SALIDA_LANDSAT) as r:
    landsat = r.read(1)
with rasterio.open("validacion/s1_observado_30m.tif") as r:
    radar = r.read(1).astype(bool)
with rasterio.open("validacion/s1_evaluable_30m.tif") as r:
    evaluable = r.read(1).astype(bool)

mapa, tiempos = niveles(MODELO)
i_sat = int(np.argmin(np.abs(tiempos - HORA_SATELITE)))
h = profundidad_30m(mapa, mapa["zs"].isel(time=i_sat).values, cota_subgrid_30m(MODELO))
modelo = np.nan_to_num(h, nan=0) >= 0.10
activo = np.isfinite(h)

despejado = landsat != 255
agua_optica = landsat == 1
zona = evaluable & activo & despejado


def fraccion_con_agua(categoria: np.ndarray) -> dict:
    total = int((categoria & zona).sum())
    con_agua = int((categoria & zona & agua_optica).sum())
    return {"km2_despejados": round(total * 0.0009, 1), "km2_con_agua_en_landsat": round(con_agua * 0.0009, 1),
            "fraccion": round(con_agua / max(total, 1), 3)}


resultado = {
    "modelo": MODELO.name, "landsat": "LC08 2017-04-04, MNDWI > 0, solo píxeles sin nube ni sombra",
    "cobertura_despejada_de_la_zona_evaluable": round(float((evaluable & activo & despejado).sum() / max((evaluable & activo).sum(), 1)), 3),
    "falsas_alarmas": fraccion_con_agua(modelo & ~radar),
    "aciertos_control": fraccion_con_agua(modelo & radar),
    "omisiones": fraccion_con_agua(~modelo & radar),
    "seco_en_ambos": fraccion_con_agua(~modelo & ~radar),
}
# Examen con referencia combinada (agua = radar O Landsat), solo donde Landsat está despejado
referencia = radar | agua_optica
a = int((modelo & referencia & zona).sum())
o = int((~modelo & referencia & zona).sum())
f = int((modelo & ~referencia & zona).sum())
resultado["examen_referencia_combinada"] = {
    "zona": "evaluable por radar, activa en el modelo y despejada en Landsat",
    "CSI": round(a / max(a + o + f, 1), 3), "tasa_acierto": round(a / max(a + o, 1), 3),
    "tasa_falsa_alarma": round(f / max(a + f, 1), 3),
    "aciertos_km2": round(a * 0.0009, 1), "omisiones_km2": round(o * 0.0009, 1), "falsas_alarmas_km2": round(f * 0.0009, 1),
}
# Mismo examen solo con radar en la misma zona despejada, para comparar en igualdad de condiciones
a2 = int((modelo & radar & zona).sum()); o2 = int((~modelo & radar & zona).sum()); f2 = int((modelo & ~radar & zona).sum())
resultado["examen_solo_radar_misma_zona"] = {"CSI": round(a2 / max(a2 + o2 + f2, 1), 3),
                                             "tasa_acierto": round(a2 / max(a2 + o2, 1), 3),
                                             "tasa_falsa_alarma": round(f2 / max(a2 + f2, 1), 3)}

Path(f"validacion/verificacion-optico-{MODELO.name}.json").write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(resultado, indent=2, ensure_ascii=False))
