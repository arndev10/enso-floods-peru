"""Funciones compartidas para leer resultados de SFINCS y llevarlos a la rejilla de 30 m del relieve FABDEM.

La usan scripts/20 (examen contra el satélite) y scripts/22 (impacto). La rejilla de 30 m es la de
datos/relieve/fabdem_bajo_piura.tif, la misma de la mancha de Sentinel-1 y de las capas de exposición.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from rasterio.warp import Resampling, reproject

REJILLA_30M = Path("datos/relieve/fabdem_bajo_piura.tif")


def rejilla_30m() -> tuple[rasterio.Affine, rasterio.crs.CRS, tuple[int, int], dict]:
    with rasterio.open(REJILLA_30M) as r:
        return r.transform, r.crs, (r.height, r.width), r.profile


def cota_subgrid_30m(modelo: Path) -> np.ndarray:
    """Relieve de 30 m que usó el subgrid de SFINCS, en la rejilla de 30 m."""
    transform, crs, forma, _ = rejilla_30m()
    cota = np.full(forma, np.nan, dtype=np.float32)
    with rasterio.open(next((modelo / "subgrid").glob("dep*.tif"))) as r:
        reproject(rasterio.band(r, 1), cota, dst_transform=transform, dst_crs=crs,
                  resampling=Resampling.nearest, dst_nodata=np.nan)
    return cota


def niveles(modelo: Path) -> tuple[xr.Dataset, pd.DatetimeIndex]:
    mapa = xr.open_dataset(modelo / "sfincs_map.nc")
    return mapa, pd.to_datetime(mapa["time"].values)


def nivel_maximo(mapa: xr.Dataset) -> np.ndarray:
    return mapa["zsmax"].max("timemax").values if "timemax" in mapa["zsmax"].dims else mapa["zsmax"].values


def _a_30m(mapa: xr.Dataset, valores: np.ndarray) -> np.ndarray:
    """Lleva un campo de las celdas de SFINCS a la rejilla de 30 m (vecino más cercano)."""
    transform, crs, forma, _ = rejilla_30m()
    x, y = mapa["x"].values, mapa["y"].values
    dx = float(abs(x[0, 1] - x[0, 0]))
    origen = rasterio.transform.from_origin(x.min() - dx / 2, y.max() + dx / 2, dx, dx)
    destino = np.full(forma, np.nan, dtype=np.float32)
    # sfincs_map.nc guarda las filas de sur a norte: se invierten para el raster
    reproject(np.flipud(valores).astype(np.float32), destino, src_transform=origen, src_crs=crs, dst_transform=transform,
              dst_crs=crs, resampling=Resampling.nearest, src_nodata=np.nan, dst_nodata=np.nan)
    return destino


def profundidad_30m(mapa: xr.Dataset, zs: np.ndarray, cota: np.ndarray) -> np.ndarray:
    """Profundidad [m] en cada píxel de 30 m = nivel de su celda de SFINCS − cota del píxel.

    SFINCS deja en NaN las celdas activas que están secas: esas cuentan como 0 m. Solo queda NaN
    lo que está fuera de las celdas activas del modelo (msk = 0).
    """
    activa = _a_30m(mapa, np.where(mapa["msk"].values > 0, 1.0, np.nan)) == 1
    nivel = _a_30m(mapa, zs)
    profundidad = np.where(np.isfinite(nivel) & (nivel > cota), nivel - cota, 0.0)
    return np.where(activa, profundidad, np.nan)


def guardar_30m(ruta: Path, datos: np.ndarray, nodata: float = np.nan) -> None:
    _, _, _, perfil = rejilla_30m()
    perfil = {**perfil, "dtype": "float32", "count": 1, "nodata": nodata, "compress": "deflate"}
    with rasterio.open(ruta, "w", **perfil) as w:
        w.write(datos.astype(np.float32), 1)
