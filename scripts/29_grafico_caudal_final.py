"""Gráfico final del caudal en Sánchez Cerro (ene–abr 2017) para el video, sin volver a correr Wflow.

Junta las corridas que ya existen:
  - Wflow con lluvia IMERG, sin ajustar (fecha correcta, magnitud baja)
  - Wflow con lluvia ERA5-Land y pérdida profunda de 20 mm/día (el ajuste elegido, scripts/24)
  - GloFAS (el sistema global europeo)
  - el pico oficial: 3,468 m³/s el 27-mar-2017 a las 12:00 (COEN-INDECI)

Lee: modelos/wflow-piura/run_default/output.csv,
     modelos/wflow-piura-era5land/sens_perdida_profunda_20/output.csv,
     datos/caudal/glofas_piura_2017-01a04.nc
Escribe: validacion/caudal-sanchez-cerro-2017.png
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import xarray as xr  # noqa: E402

UMBRAL_CIUDAD = 1900


def wflow(ruta: str) -> pd.Series:
    serie = pd.read_csv(ruta, parse_dates=["time"], index_col="time").filter(like="river_q").iloc[:, 0]
    return serie["2017-01-01":"2017-04-30"]


imerg = wflow("modelos/wflow-piura/run_default/output.csv")
ajustado = wflow("modelos/wflow-piura-era5land/sens_perdida_profunda_20/output.csv")
glofas = xr.open_dataset("datos/caudal/glofas_piura_2017-01a04.nc")["avg_dis"]
glofas = glofas.sel(latitude=-5.025, longitude=360 - 80.625, method="nearest").to_series()["2017-01-01":"2017-04-30"]

fig, eje = plt.subplots(figsize=(11, 4.8))
fig.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.12)
eje.axhline(UMBRAL_CIUDAD, color="#d62728", linestyle=":", linewidth=1)
eje.text(pd.Timestamp("2017-01-03"), UMBRAL_CIUDAD + 60, "desde aquí se inunda la ciudad (~1,900 m³/s)", color="#d62728", fontsize=9)
eje.plot(ajustado, color="#1f6fff", linewidth=2.2, label=f"Mi modelo ajustado (pico {ajustado.max():,.0f} m³/s)")
eje.plot(imerg, color="#7cc0f5", linewidth=1.4, label="Mi modelo sin ajustar, lluvia de la NASA")
eje.plot(glofas, color="gray", linestyle="--", linewidth=1.4, label=f"GloFAS, sistema global (pico {glofas.max():,.0f} m³/s)")
eje.scatter([pd.Timestamp("2017-03-27 12:00")], [3468], color="crimson", s=70, zorder=5, label="Pico oficial: 3,468 m³/s (COEN-INDECI)")
eje.set_ylabel("Caudal (m³/s)")
eje.set_title("Río Piura en el puente Sánchez Cerro — enero a abril de 2017")
eje.legend(loc="upper left", fontsize=9)
eje.spines[["top", "right"]].set_visible(False)
fig.savefig("validacion/caudal-sanchez-cerro-2017.png", dpi=120)
print(f"validacion/caudal-sanchez-cerro-2017.png · ajustado {ajustado.max():,.0f} ({ajustado.idxmax():%d-%b}) · "
      f"IMERG {imerg.max():,.0f} · GloFAS {glofas.max():,.0f}")
