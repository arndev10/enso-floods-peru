"""Convierte las capas crudas de Earth Engine y ERA5 en un catálogo de datos de HydroMT para Piura.

Replica el formato del catálogo de ejemplo de Deltares (artifact_data): mismos nombres de
variables, tipos y valores de "sin dato". Las unidades quedan ya convertidas a las finales,
así el catálogo no necesita factores de conversión.

- merit_hydro/: elevtn, flwdir (d8), uparea, upgrid, rivwth, hnd + strord, basins y lndslp
  calculados con pyflwdir.
- merit_hydro_index.gpkg: polígonos de cuencas con el mismo `basid` que el raster basins.
- soilgrids/: {bd, clyppt, sltppt, sndppt, oc, ph}_sl1..6 (formato soilgrids_2020) + soilthickness.
- modis_lai.nc: climatología mensual (time = 1..12).
- era5 / era5_orografia: los escribe scripts/10_bajar_era5_diario.py.

Corre en el entorno wflow: pixi run -e wflow python scripts/12_armar_catalogo_wflow.py
Lee: datos/wflow/crudo_gee/*.tif. Escribe: datos/wflow/{merit_hydro,soilgrids}/, catalogo_piura.yml.
"""
from pathlib import Path

import geopandas as gpd
import numpy as np
import pyflwdir
import rasterio
import xarray as xr
from rasterio import features

CRUDO = Path("datos/wflow/crudo_gee")
SALIDA = Path("datos/wflow")
(SALIDA / "merit_hydro").mkdir(parents=True, exist_ok=True)
(SALIDA / "soilgrids").mkdir(parents=True, exist_ok=True)

ESPESOR_SUELO_CM = 200  # SoilGrids 2.0 no trae profundidad a la roca: se asume 2 m (su límite)


def leer(nombre: str, banda: int = 1) -> tuple[np.ndarray, dict]:
    with rasterio.open(CRUDO / f"{nombre}.tif") as r:
        return r.read(banda), r.profile


def escribir(ruta: Path, datos: np.ndarray, perfil: dict, tipo: str, nodata) -> None:
    perfil = {**perfil, "dtype": tipo, "nodata": nodata, "count": 1, "compress": "deflate"}
    with rasterio.open(ruta, "w", **perfil) as w:
        w.write(datos.astype(tipo), 1)


# --- MERIT Hydro --------------------------------------------------------------------
elv, perfil = leer("merit_elv")
direccion, _ = leer("merit_dir")
transform = perfil["transform"]

# MERIT: 0 = desembocadura, 255 (−1 en origen) = sumidero interior, −9 = mar/sin dato
flwdir = direccion.astype(np.int16)
flwdir = np.where(np.isin(flwdir, [0, 255]), 0, flwdir)  # pyflwdir d8: 0 = sumidero
flwdir = np.where(flwdir == -9, 247, flwdir).astype(np.uint8)  # 247 = sin dato
flw = pyflwdir.from_array(flwdir, ftype="d8", transform=transform, latlon=True)

strord = flw.stream_order(type="strahler").astype(np.int32)
basins = flw.basins().astype(np.uint32)
lndslp = pyflwdir.dem.slope(elv.astype(np.float32), nodata=-9999, latlon=True, transform=transform)

capas_merit = {
    "elevtn": (elv, "float32", -9999.0),
    "flwdir": (flwdir, "uint8", 247),
    "uparea": (leer("merit_upa")[0], "float32", -9999.0),
    "upgrid": (leer("merit_upg")[0], "int32", -9999),
    "rivwth": (leer("merit_wth")[0], "float32", -9999.0),
    "hnd": (leer("merit_hnd")[0], "float32", -9999.0),
    "strord": (np.where(flwdir == 247, 255, strord), "uint8", 255),
    "basins": (basins, "uint32", 0),
    "lndslp": (np.where(elv == -9999, -9999.0, lndslp), "float32", -9999.0),
}
for nombre, (datos, tipo, nodata) in capas_merit.items():
    escribir(SALIDA / "merit_hydro" / f"{nombre}.tif", datos, perfil, tipo, nodata)
print(f"merit_hydro: {len(capas_merit)} capas, {len(np.unique(basins)) - 1} cuencas")

# Índice de cuencas: un polígono por basid (solo cuencas de más de ~10 km² para no inflarlo)
ids, conteo = np.unique(basins[basins > 0], return_counts=True)
grandes = set(ids[conteo > 1200].tolist())  # ~1200 celdas de 90 m ≈ 10 km²
poligonos = [
    {"basid": int(valor), "geometry": geom}
    for geom, valor in features.shapes(basins.astype(np.int32), mask=np.isin(basins, list(grandes)), transform=transform)
]
indice = gpd.GeoDataFrame.from_features(
    [{"type": "Feature", "properties": {"basid": p["basid"]}, "geometry": p["geometry"]} for p in poligonos], crs=4326
).dissolve("basid").reset_index()
indice.to_file(SALIDA / "merit_hydro_index.gpkg", driver="GPKG")
print(f"merit_hydro_index: {len(indice)} cuencas > 10 km²")

# --- SoilGrids 2.0 → formato soilgrids_2020 de hydromt_wflow -------------------------
# Unidades ISRIC → finales: bdod cg/cm³ ×0.01 = g/cm³ · clay/silt/sand g/kg ×0.1 = % ·
# soc dg/kg ×0.01 = % · phh2o pH×10 ×0.1 = pH
conversion = {"bdod": ("bd", 0.01), "clay": ("clyppt", 0.1), "silt": ("sltppt", 0.1),
              "sand": ("sndppt", 0.1), "soc": ("oc", 0.01), "phh2o": ("ph", 0.1)}
for variable, (nombre, factor) in conversion.items():
    with rasterio.open(CRUDO / f"soilgrids_{variable}.tif") as r:
        perfil_suelo = r.profile
        for capa in range(1, 7):
            datos = r.read(capa)
            escribir(SALIDA / "soilgrids" / f"{nombre}_sl{capa}.tif",
                     np.where(datos < 0, -9999.0, datos * factor), perfil_suelo, "float32", -9999.0)
        if variable == "bdod":  # el espesor se marca donde hay dato de suelo
            con_dato = r.read(1) >= 0
            escribir(SALIDA / "soilgrids" / "soilthickness.tif",
                     np.where(con_dato, ESPESOR_SUELO_CM, -9999.0), perfil_suelo, "float32", -9999.0)
print("soilgrids: 36 capas + soilthickness")

# --- MODIS LAI ------------------------------------------------------------------------
lai = xr.open_dataarray(CRUDO / "modis_lai_clim.tif", engine="rasterio")
lai = lai.rename({"band": "time"}).assign_coords(time=np.arange(1, 13)).rename("LAI")
lai = lai.drop_vars([c for c in lai.coords if c not in ("time", "x", "y", "spatial_ref")])
lai.to_dataset().to_netcdf(SALIDA / "modis_lai.nc")
print("modis_lai: 12 meses")

# --- Catálogo -------------------------------------------------------------------------
raiz = SALIDA.resolve().as_posix()
catalogo = f"""meta:
  version: v0.1.0
  name: catalogo_piura
  root: {raiz}
  hydromt_version: '>1.0a,<2'

merit_hydro:
  data_type: RasterDataset
  uri: merit_hydro/{{variable}}.tif
  driver: {{name: rasterio}}
  metadata: {{crs: 4326, category: topography, url: "Earth Engine MERIT/Hydro/v1_0_1"}}

merit_hydro_index:
  data_type: GeoDataFrame
  uri: merit_hydro_index.gpkg
  driver: {{name: pyogrio}}
  metadata: {{crs: 4326, category: topography}}

soilgrids_2020:
  data_type: RasterDataset
  uri: soilgrids/{{variable}}.tif
  driver: {{name: rasterio}}
  metadata: {{crs: 4326, category: soil, url: "Earth Engine projects/soilgrids-isric",
             notes: "SoilGrids 2.0; soilthickness constante de {ESPESOR_SUELO_CM} cm"}}

modis_lai:
  data_type: RasterDataset
  uri: modis_lai.nc
  driver: {{name: raster_xarray}}
  metadata: {{crs: 4326, category: landuse, url: "Earth Engine MODIS/061/MCD15A3H, clim. 2010-2020"}}

era5_diario:
  data_type: RasterDataset
  uri: era5_diario_2016-07a2017-05.nc
  driver: {{name: raster_xarray}}
  metadata: {{crs: 4326, category: meteo, url: "Copernicus CDS derived-era5-single-levels-daily-statistics"}}

era5land_diario:
  data_type: RasterDataset
  uri: era5land_diario_2016-07a2017-05.nc
  driver: {{name: raster_xarray}}
  metadata: {{crs: 4326, category: meteo, url: "Earth Engine ECMWF/ERA5_LAND/DAILY_AGGR (scripts/16)"}}

era5land_diario_1998:
  data_type: RasterDataset
  uri: era5land_diario_1997-07a1998-05.nc
  driver: {{name: raster_xarray}}
  metadata: {{crs: 4326, category: meteo, url: "Earth Engine ECMWF/ERA5_LAND/DAILY_AGGR (scripts/16), Niño 1997-98"}}

era5land_orografia:
  data_type: RasterDataset
  uri: era5land_orografia.nc
  driver: {{name: raster_xarray}}
  metadata: {{crs: 4326, category: meteo, notes: "elevación media de MERIT a 0.1°"}}

imerg_diario:
  data_type: RasterDataset
  uri: imerg_diario_2016-07a2017-05.nc
  driver: {{name: raster_xarray}}
  metadata: {{crs: 4326, category: meteo, url: "Earth Engine NASA/GPM_L3/IMERG_V07 (scripts/14)"}}

era5_orografia:
  data_type: RasterDataset
  uri: era5_orografia.nc
  driver: {{name: raster_xarray}}
  metadata: {{crs: 4326, category: meteo}}

rivers_lin2019:
  data_type: GeoDataFrame
  uri: rivers_lin2019_piura.gpkg
  driver: {{name: pyogrio}}
  metadata: {{crs: 4326, category: hydrography, url: "https://zenodo.org/records/3552776",
             notes: "Lin et al. 2019, recortado a Piura por scripts/13_recortar_rios_lin.py"}}

esa_worldcover:
  data_type: RasterDataset
  uri: crudo_gee/esa_worldcover.tif
  driver: {{name: rasterio}}
  metadata: {{crs: 4326, category: landuse, url: "Earth Engine ESA/WorldCover/v200 a 3″ (toda la cuenca)"}}
"""
(SALIDA / "catalogo_piura.yml").write_text(catalogo, encoding="utf-8")
print(f"Catálogo → {SALIDA / 'catalogo_piura.yml'}")
