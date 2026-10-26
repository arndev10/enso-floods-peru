"""Corre Wflow (Julia) sobre uno o varios modelos de Piura y compara el caudal en Sánchez Cerro.

Uso (entorno wflow): pixi run -e wflow python scripts/17_correr_wflow_y_comparar.py modelos/wflow-piura [modelos/otro ...]

Para cada modelo: corre `Wflow.run` con el proyecto Julia del repo (julia/), lee output.csv y
saca el pico del caudal en la estación. Compara con GloFAS y con el pico reportado en prensa
(3,468 m³/s el 27-mar-2017 a las 12:00, COEN-INDECI).

Lee: <modelo>/wflow_sbm.toml, datos/caudal/glofas_piura_2017-01a04.nc.
Escribe: <modelo>/run_default/output.csv (Wflow), validacion/caudal-sanchez-cerro-2017.png
"""
import subprocess
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import xarray as xr  # noqa: E402

PICO_REPORTADO = 3468  # m³/s, 27-mar-2017 12:00 (COEN-INDECI, citado en decreto supremo)
modelos = [Path(m) for m in sys.argv[1:]] or [Path("modelos/wflow-piura")]

series = {}
for modelo in modelos:
    inicio = time.time()
    resultado = subprocess.run(
        ["julia", "--project=julia", "-e", f'using Wflow; Wflow.run(raw"{(modelo / "wflow_sbm.toml").resolve()}")'],
        capture_output=True, text=True,
    )
    if resultado.returncode != 0:
        print(resultado.stdout[-3000:], resultado.stderr[-3000:])
        raise SystemExit(f"Wflow falló en {modelo}")
    salida = pd.read_csv(modelo / "run_default" / "output.csv", parse_dates=["time"], index_col="time")
    columna = [c for c in salida.columns if c.startswith("river_q") and "estaciones" in c] or [
        c for c in salida.columns if c.startswith("river_q")]
    serie = salida[columna[0]]
    series[modelo.name] = serie
    print(f"{modelo.name}: corrió en {time.time() - inicio:.0f} s · pico {serie.max():,.0f} m³/s el {serie.idxmax():%d-%b-%Y}")

# GloFAS en la celda del río (lat -5.025, lon -80.625)
glofas = xr.open_dataset("datos/caudal/glofas_piura_2017-01a04.nc")["avg_dis"]
glofas = glofas.sel(latitude=-5.025, longitude=360 - 80.625, method="nearest").to_series()

fig, eje = plt.subplots(figsize=(11, 4.5), constrained_layout=True)
for nombre, serie in series.items():
    eje.plot(serie["2017-01-01":"2017-04-30"], linewidth=1.8, label=f"Wflow — {nombre}")
eje.plot(glofas, color="gray", linestyle="--", label="GloFAS (modelo global europeo)")
eje.scatter([pd.Timestamp("2017-03-27 12:00")], [PICO_REPORTADO], color="crimson", zorder=5,
            label="Pico oficial: 3,468 m³/s (COEN-INDECI)")
eje.set_ylabel("Caudal (m³/s)")
eje.set_title("Río Piura en el puente Sánchez Cerro — enero a abril de 2017")
eje.legend(loc="upper left")
eje.spines[["top", "right"]].set_visible(False)
fig.savefig("validacion/caudal-sanchez-cerro-2017.png", dpi=120)
print("Figura: validacion/caudal-sanchez-cerro-2017.png")
