"""Delimita la cuenca del río Piura aguas arriba de la ciudad, con HydroBASINS (nivel 12) en Earth Engine.

Método: toma la subcuenca que contiene el punto de control (puente Sánchez Cerro) y
suma todas las subcuencas que drenan hacia ella siguiendo NEXT_DOWN. También arma la
cuenca completa hasta el mar (incluye el Bajo Piura) para el dominio de inundación.

Lee: GEE_PROJECT del .env. Escribe: geo/cuenca-piura-hasta-ciudad.geojson,
geo/cuenca-piura-completa.geojson (archivos chicos, sí van a git).
"""
import json
import os
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)

import ee  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv()
ee.Initialize(project=os.environ["GEE_PROJECT"])

PUNTO_CONTROL = ee.Geometry.Point([-80.6265, -5.1945])  # puente Sánchez Cerro (aprox.)
RECUADRO = ee.Geometry.Rectangle([-81.3, -6.0, -79.2, -4.6])  # región que contiene toda la cuenca

basins = ee.FeatureCollection("WWF/HydroSHEDS/v1/Basins/hybas_12").filterBounds(RECUADRO)
tabla = basins.reduceColumns(ee.Reducer.toList(3), ["HYBAS_ID", "NEXT_DOWN", "SUB_AREA"]).get("list").getInfo()
siguiente = {int(h): int(n) for h, n, _ in tabla}
area = {int(h): a for h, _, a in tabla}

semilla = int(basins.filterBounds(PUNTO_CONTROL).first().get("HYBAS_ID").getInfo())


def aguas_arriba(desde: int) -> set[int]:
    """Todas las subcuencas cuyo camino de drenaje pasa por `desde` (incluida)."""
    resultado = set()
    for hybas in siguiente:
        actual = hybas
        while actual and actual in siguiente:
            if actual == desde:
                resultado.add(hybas)
                break
            actual = siguiente[actual]
    return resultado


def desembocadura(desde: int) -> int:
    """Sigue NEXT_DOWN hasta la última subcuenca antes del mar."""
    actual = desde
    while siguiente.get(actual) in siguiente:
        actual = siguiente[actual]
    return actual


hasta_ciudad = aguas_arriba(semilla)
completa = aguas_arriba(desembocadura(semilla))

Path("geo").mkdir(exist_ok=True)
for nombre, ids in (("hasta-ciudad", hasta_ciudad), ("completa", completa)):
    geometria = basins.filter(ee.Filter.inList("HYBAS_ID", list(ids))).union(maxError=50).geometry()
    caja = geometria.bounds().coordinates().getInfo()[0]
    km2 = sum(area[i] for i in ids)
    salida = Path(f"geo/cuenca-piura-{nombre}.geojson")
    salida.write_text(
        json.dumps(
            {
                "type": "Feature",
                "properties": {"nombre": f"Cuenca del río Piura ({nombre})", "area_km2": round(km2), "subcuencas": len(ids)},
                "geometry": geometria.simplify(100).getInfo(),
            }
        ),
        encoding="utf-8",
    )
    lons = [p[0] for p in caja]
    lats = [p[1] for p in caja]
    print(f"{nombre:13} {km2:>8,.0f} km²  {len(ids):>4} subcuencas  "
          f"lon {min(lons):.2f} a {max(lons):.2f}  lat {min(lats):.2f} a {max(lats):.2f}  → {salida}")
