"""Impacto de un escenario de inundación (Fase 4): cuántas casas, personas, colegios, centros de salud y km de vías.

Usa la profundidad MÁXIMA del evento a 30 m y la traduce al cuerpo humano (para el público):
  < 10 cm: sin afectación · 10–30 cm: tobillo · 30–60 cm: rodilla · 60–120 cm: cintura ·
  120–180 cm: pecho · > 180 cm: sobre la cabeza.

Exposición (todo a 30 m o puntos):
  - edificios: Google Open Buildings v3, la ciudad de HOY (datos/exposicion/edificios_hoy.tif, banda 1)
  - personas: WorldPop 2017 (datos/exposicion/worldpop_2017.tif)
  - colegios y centros de salud: OpenStreetMap (geo/osm-educacion.geojson, geo/osm-salud.geojson)
  - vías principales: OpenStreetMap (geo/osm-vias.geojson); se cuentan km con ≥ 30 cm de agua

Es una estimación de EXPOSICIÓN (qué queda bajo el agua), no de daño económico. El daño con curvas
profundidad–daño queda para Delft-FIAT.

Entorno por defecto: pixi run python scripts/22_impacto.py [modelos/sfincs-...]
Escribe: <modelo>/profundidad_max_30m.tif, validacion/impacto-<modelo>.json y .csv
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from shapely.geometry import LineString

sys.path.insert(0, str(Path(__file__).parent))
from util_sfincs import cota_subgrid_30m, guardar_30m, nivel_maximo, niveles, profundidad_30m, rejilla_30m  # noqa: E402

MODELO = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("modelos/sfincs-bajo-piura")
CLASES = [(0.10, 0.30, "tobillo"), (0.30, 0.60, "rodilla"), (0.60, 1.20, "cintura"),
          (1.20, 1.80, "pecho"), (1.80, np.inf, "sobre la cabeza")]

mapa, _ = niveles(MODELO)
profundidad = profundidad_30m(mapa, nivel_maximo(mapa), cota_subgrid_30m(MODELO))
guardar_30m(MODELO / "profundidad_max_30m.tif", profundidad)
h = np.nan_to_num(profundidad, nan=0.0)

with rasterio.open("datos/exposicion/edificios_hoy.tif") as r:
    edificios = r.read(1).astype(np.float64)
with rasterio.open("datos/exposicion/worldpop_2017.tif") as r:
    personas = r.read(1).astype(np.float64)

transform, crs, forma, _ = rejilla_30m()


def profundidad_en_puntos(ruta: str) -> np.ndarray:
    puntos = gpd.read_file(ruta).to_crs(crs)
    filas, columnas = rasterio.transform.rowcol(transform, puntos.geometry.x.values, puntos.geometry.y.values)
    filas, columnas = np.asarray(filas), np.asarray(columnas)
    dentro = (filas >= 0) & (filas < forma[0]) & (columnas >= 0) & (columnas < forma[1])
    valores = np.zeros(len(puntos))
    valores[dentro] = h[filas[dentro], columnas[dentro]]
    return valores


h_colegios = profundidad_en_puntos("geo/osm-educacion.geojson")
h_salud = profundidad_en_puntos("geo/osm-salud.geojson")

filas = []
for minimo, maximo, nombre in CLASES:
    en_clase = (h >= minimo) & (h < maximo)
    filas.append({
        "profundidad": nombre, "rango_m": f"{minimo:g}–{maximo:g}" if np.isfinite(maximo) else f"> {minimo:g}",
        "area_km2": round(en_clase.sum() * 0.0009, 1),
        "edificios": int(edificios[en_clase].sum()),
        "personas": int(round(personas[en_clase].sum(), -2)),
        "colegios": int(((h_colegios >= minimo) & (h_colegios < maximo)).sum()),
        "salud": int(((h_salud >= minimo) & (h_salud < maximo)).sum()),
    })
tabla = pd.DataFrame(filas)
total = tabla[["area_km2", "edificios", "personas", "colegios", "salud"]].sum()

# Vías: km con al menos 30 cm de agua (se muestrea cada ~30 m a lo largo de cada tramo)
vias = gpd.read_file("geo/osm-vias.geojson").to_crs(crs)
km_cortados = 0.0
for linea in vias.geometry:
    if not isinstance(linea, LineString) or linea.length == 0:
        continue
    distancias = np.arange(0, linea.length, 30.0)
    xs, ys = zip(*[linea.interpolate(d).coords[0] for d in distancias])
    f, c = rasterio.transform.rowcol(transform, xs, ys)
    f, c = np.asarray(f), np.asarray(c)
    ok = (f >= 0) & (f < forma[0]) & (c >= 0) & (c < forma[1])
    km_cortados += (h[f[ok], c[ok]] >= 0.30).sum() * 0.030

nombre = MODELO.name
tabla.to_csv(f"validacion/impacto-{nombre}.csv", index=False)
resumen = {
    "modelo": nombre, "nota": "Exposición (qué queda bajo ≥10 cm de agua en el máximo del evento), no daño económico.",
    "area_inundada_km2": round(float(total["area_km2"]), 1), "edificios": int(total["edificios"]),
    "personas": int(total["personas"]), "colegios": int(total["colegios"]), "centros_salud": int(total["salud"]),
    "km_vias_principales_con_30cm_o_mas": round(km_cortados, 1),
    "por_profundidad": filas,
    "fuentes": {"edificios": "Google Open Buildings v3 (la ciudad de hoy)", "personas": "WorldPop 2017",
                "colegios_y_salud_y_vias": "OpenStreetMap (oct-2026)"},
}
Path(f"validacion/impacto-{nombre}.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")

print(tabla.to_string(index=False))
print(f"\nTOTAL ({nombre}): {total['area_km2']:.0f} km² · {int(total['edificios']):,} edificios · "
      f"{int(total['personas']):,} personas · {int(total['colegios'])} colegios · {int(total['salud'])} centros de salud · "
      f"{km_cortados:.0f} km de vías principales con ≥ 30 cm")
