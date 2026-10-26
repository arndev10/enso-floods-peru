"""Gráfico de la lluvia diaria promedio sobre la cuenca del Piura (ene-abr 2017) según IMERG y, si ya está, ERA5.

Lee: datos/wflow/imerg_diario_2016-07a2017-05.nc, datos/wflow/era5_diario_2016-07a2017-05.nc (opcional),
     geo/cuenca-piura-hasta-ciudad.geojson.
Escribe: validacion/lluvia-cuenca-2017.png y validacion/lluvia-cuenca-2017.csv
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from rasterio.features import geometry_mask  # noqa: E402
from rasterio.transform import from_origin  # noqa: E402
import shapely.geometry  # noqa: E402
import xarray as xr  # noqa: E402

cuenca = shapely.geometry.shape(
    json.loads(Path("geo/cuenca-piura-hasta-ciudad.geojson").read_text(encoding="utf-8"))["geometry"]
)


def promedio_cuenca(ruta: Path) -> pd.Series:
    precip = xr.open_dataset(ruta)["precip"].sel(time=slice("2017-01-01", "2017-04-30"))
    lon, lat = precip.longitude.values, precip.latitude.values
    dx, dy = abs(lon[1] - lon[0]), abs(lat[1] - lat[0])
    transform = from_origin(lon.min() - dx / 2, lat.max() + dy / 2, dx, dy)
    dentro = ~geometry_mask([cuenca], (lat.size, lon.size), transform, all_touched=True)
    if lat[0] < lat[-1]:  # rejilla de sur a norte: voltear la máscara
        dentro = dentro[::-1]
    mascara = xr.DataArray(dentro, dims=("latitude", "longitude"), coords={"latitude": lat, "longitude": lon})
    return precip.where(mascara).mean(["latitude", "longitude"]).to_series()


series = {"IMERG (satélite NASA)": promedio_cuenca(Path("datos/wflow/imerg_diario_2016-07a2017-05.nc"))}
era5 = Path("datos/wflow/era5_diario_2016-07a2017-05.nc")
if era5.exists():
    series["ERA5 (reanálisis europeo)"] = promedio_cuenca(era5)

tabla = pd.DataFrame(series)
tabla.round(1).to_csv("validacion/lluvia-cuenca-2017.csv", index_label="fecha")

fig, eje = plt.subplots(figsize=(11, 4.5), constrained_layout=True)
colores = {"IMERG (satélite NASA)": "#1f6fff", "ERA5 (reanálisis europeo)": "#ff7a00"}
for nombre, serie in tabla.items():
    eje.bar(serie.index, serie.values, width=0.9 if len(tabla.columns) == 1 else 0.45,
            align="edge" if nombre.startswith("ERA5") else "center", color=colores[nombre], label=nombre)
eje.axvline(pd.Timestamp("2017-03-27"), color="crimson", linestyle="--", linewidth=1.2)
eje.text(pd.Timestamp("2017-03-27"), eje.get_ylim()[1] * 0.95, " desborde en la ciudad\n 27-mar-2017",
         color="crimson", va="top", fontsize=9)
eje.set_ylabel("Lluvia promedio sobre la cuenca (mm/día)")
eje.set_title("Río Piura hasta la ciudad — lluvia diaria, enero a abril de 2017")
eje.legend(loc="upper left")
eje.spines[["top", "right"]].set_visible(False)
fig.savefig("validacion/lluvia-cuenca-2017.png", dpi=120)

for nombre, serie in tabla.items():
    print(f"{nombre}: total ene-abr {serie.sum():.0f} mm · marzo {serie['2017-03'].sum():.0f} mm · "
          f"día más lluvioso {serie.idxmax():%d-%b} ({serie.max():.0f} mm)")
