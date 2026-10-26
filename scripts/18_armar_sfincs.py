"""Arma el modelo SFINCS del Bajo Piura para el evento de marzo de 2017 (Fase 3).

- Dominio: ciudad de Piura → Bajo Piura → depresión de Sechura (UTM 17S), celdas de 120 m con
  subgrid de 30 m (FABDEM): el cauce del río (100–200 m) queda representado sin correr todo a 30 m.
- Celdas activas: cota < 80 m (el agua no sube al tablazo). Borde abierto con el mar a nivel 0.
- Rugosidad: ESA WorldCover con la tabla de hydromt_sfincs.
- Entrada del río: HIDROGRAMA DE DISEÑO = forma de la crecida de Wflow con lluvia IMERG (que clava
  la fecha del pico, 27-mar) escalada al pico oficial de 3,468 m³/s (COEN-INDECI).
- Lluvia local: IMERG promedio sobre el dominio (mm/día → mm/h).
- Simulación: --inicio (por defecto 1-mar-2017) → 1-abr-2017 12:00 UTC (pasada de Sentinel-1: 1-abr 11:01 UTC).

Entorno por defecto: pixi run python scripts/18_armar_sfincs.py [carpeta_modelo] [--qinf MM_H] [--inicio AAAA-MM-DD]
  --qinf: infiltración constante en tierra [mm/h] (0 = sin infiltración, como la primera corrida)
  --inicio: fecha de inicio de la simulación (por defecto 2017-03-01)
Lee: datos/relieve/fabdem_bajo_piura.tif, datos/exposicion/worldcover_2021.tif,
     modelos/wflow-piura/run_default/output.csv, datos/wflow/imerg_diario_2016-07a2017-05.nc
Escribe: modelos/sfincs-bajo-piura/ (no va a git), datos/catalogo_sfincs.yml
"""
import argparse
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from hydromt_sfincs import SfincsModel
from shapely.geometry import Point

# hydromt_sfincs 1.2.2 llama a Index.is_integer(), is_numeric(), etc., que pandas 2.x eliminó.
# Se restauran con sus equivalentes de pandas.api.types:
for _metodo, _prueba in {"is_integer": pd.api.types.is_integer_dtype, "is_numeric": pd.api.types.is_numeric_dtype,
                         "is_floating": pd.api.types.is_float_dtype, "is_boolean": pd.api.types.is_bool_dtype,
                         "is_object": pd.api.types.is_object_dtype}.items():
    if not hasattr(pd.Index, _metodo):
        setattr(pd.Index, _metodo, lambda self, _p=_prueba: _p(self))

parser = argparse.ArgumentParser()
parser.add_argument("carpeta", nargs="?", default="modelos/sfincs-bajo-piura")
parser.add_argument("--qinf", type=float, default=0.0)
parser.add_argument("--inicio", default="2017-03-01")
args = parser.parse_args()
RAIZ_MODELO = Path(args.carpeta)
PICO_DISENO = 3468.0  # m³/s, pico del 27-mar-2017 12:00 (COEN-INDECI, citado en decreto supremo)
INICIO, FIN = pd.Timestamp(args.inicio).strftime("%Y%m%d %H%M%S"), "20170401 120000"
DX = 120  # m
SUBPIXELES = 4  # 120 m / 4 = 30 m, la resolución de FABDEM (SFINCS exige un número par)
ENTRADA_RIO = (-80.6271, -5.0596)  # donde el río entra al dominio (MERIT, 7,202 km²)
PUNTOS_OBS = {"Puente Sanchez Cerro": (-80.6265, -5.1945), "Catacaos": (-80.675, -5.265),
              "Cura Mori": (-80.66, -5.32), "Laguna La Nina (centro)": (-80.62, -5.75)}

# --- Catálogo de datos (formato HydroMT 0.x del entorno por defecto) -----------------------
datos = Path("datos").resolve().as_posix()
catalogo = Path("datos/catalogo_sfincs.yml")
catalogo.write_text(f"""root: {datos}
fabdem_bajo_piura:
  path: relieve/fabdem_bajo_piura.tif
  data_type: RasterDataset
  driver: raster
  crs: 32717
  nodata: -.inf
  meta: {{source_url: "Earth Engine projects/sat-io/open-datasets/FABDEM"}}
worldcover_bajo_piura:
  path: exposicion/worldcover_2021.tif
  data_type: RasterDataset
  driver: raster
  crs: 32717
  meta: {{source_url: "Earth Engine ESA/WorldCover/v200"}}
""", encoding="utf-8")

# --- Rejilla alineada al relieve -------------------------------------------------------------
with rasterio.open("datos/relieve/fabdem_bajo_piura.tif") as r:
    b = r.bounds
mmax, nmax = int((b.right - b.left) // DX), int((b.top - b.bottom) // DX)

sf = SfincsModel(root=str(RAIZ_MODELO), mode="w+", data_libs=[str(catalogo)])
sf.setup_grid(x0=b.left, y0=b.bottom, dx=DX, dy=DX, nmax=nmax, mmax=mmax, rotation=0, epsg=32717)
sf.setup_dep(datasets_dep=[{"elevtn": "fabdem_bajo_piura"}])
sf.setup_mask_active(zmin=-5, zmax=80, fill_area=10, drop_area=5)
sf.setup_mask_bounds(btype="waterlevel", zmax=1.0)  # celdas del borde junto al mar

ruta_mapeo = Path(__import__("hydromt_sfincs").__file__).parent / "data" / "lulc" / "esa_worldcover_mapping.csv"
rugosidad = [{"lulc": "worldcover_bajo_piura", "reclass_table": str(ruta_mapeo)}]
sf.setup_subgrid(datasets_dep=[{"elevtn": "fabdem_bajo_piura"}], datasets_rgh=rugosidad,
                 nr_subgrid_pixels=SUBPIXELES, write_dep_tif=True, write_man_tif=False)

sf.setup_config(tref=INICIO, tstart=INICIO, tstop=FIN, dtout=3600, dtmaxout=86400 * 40,
                dthisout=600, alpha=0.5, advection=0, qinf=args.qinf)

# --- Nivel del mar: 0 m constante ----------------------------------------------------------
tiempos = pd.date_range(args.inicio, "2017-04-01 12:00", freq="1h")
mar = gpd.GeoDataFrame({"index": [1]}, geometry=[Point(-81.0, -5.4)], crs=4326).to_crs(32717)
sf.setup_waterlevel_forcing(timeseries=pd.DataFrame({1: 0.0}, index=tiempos), locations=mar, buffer=200000)

# --- Hidrograma de diseño del río -----------------------------------------------------------
wflow = pd.read_csv("modelos/wflow-piura/run_default/output.csv", parse_dates=["time"], index_col="time")
q = wflow.filter(like="river_q").iloc[:, 0]
factor = PICO_DISENO / q.max()
# La forma viene de Wflow (diaria); el pico se ancla a la hora observada: 27-mar-2017 12:00 hora de
# Perú = 17:00 UTC (COEN-INDECI). Así se corrige el desfase de convención de fechas entre la
# lluvia diaria y la salida de Wflow (≈ 1 día).
PICO_OBSERVADO_UTC = pd.Timestamp("2017-03-27 17:00")
q_diseno = (q * factor).copy()
q_diseno.index = q_diseno.index + (PICO_OBSERVADO_UTC - q_diseno.idxmax())
q_diseno = q_diseno.reindex(q_diseno.index.union(tiempos)).interpolate("time").reindex(tiempos)
entrada = gpd.GeoDataFrame({"index": [1]}, geometry=[Point(*ENTRADA_RIO)], crs=4326).to_crs(32717)
sf.setup_discharge_forcing(timeseries=pd.DataFrame({1: q_diseno.values}, index=tiempos), locations=entrada)

# --- Lluvia local IMERG promedio sobre el dominio (mm/día → mm/h, constante en el día) --------
imerg = xr.open_dataset("datos/wflow/imerg_diario_2016-07a2017-05.nc")["precip"]
imerg = imerg.sel(longitude=slice(-81.0, -80.4), latitude=slice(-5.05, -6.0)).mean(["latitude", "longitude"])
lluvia = (imerg.to_series() / 24).reindex(tiempos, method="ffill").fillna(0)
sf.setup_precip_forcing(timeseries=pd.DataFrame({"precip": lluvia.values}, index=tiempos))

# --- Puntos de observación y escritura --------------------------------------------------------
obs = gpd.GeoDataFrame({"name": list(PUNTOS_OBS)}, geometry=[Point(*xy) for xy in PUNTOS_OBS.values()],
                       crs=4326).to_crs(32717)
sf.setup_observation_points(locations=obs, merge=False)
sf.write()

activas = int((sf.mask > 0).sum())
print(f"SFINCS → {RAIZ_MODELO}: rejilla {mmax}×{nmax} de {DX} m, {activas:,} celdas activas, subgrid de 30 m")
print(f"Hidrograma de diseño: Wflow-IMERG × {factor:.2f} → pico {q_diseno.max():,.0f} m³/s el {q_diseno.idxmax():%d-%b %H:%M}")
print(f"Lluvia local total {args.inicio} a 1-abr: {lluvia.sum():.0f} mm · infiltración {args.qinf} mm/h")
