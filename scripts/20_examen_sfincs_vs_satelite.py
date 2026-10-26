"""El "examen" del modelo: compara la inundación simulada por SFINCS con la que vio Sentinel-1 el 1-abr-2017.

1. Lleva el nivel de agua de SFINCS (celdas de 120 m) al relieve de 30 m del subgrid:
   profundidad = nivel − cota en cada píxel de 30 m (scripts/util_sfincs.py).
2. Compara dos momentos: el nivel a la hora de la pasada del satélite (1-abr 11:00 UTC) y el
   máximo de todo el evento.
3. Solo se evalúa donde el radar puede juzgar (validacion/s1_evaluable_30m.tif) y donde SFINCS
   está activo. Un píxel cuenta como inundado si tiene ≥ 10 cm de agua.
Métricas: aciertos (A), omisiones (O: el satélite vio agua y el modelo no), falsas alarmas
(F: el modelo pone agua y el satélite no). CSI = A/(A+O+F); tasa de acierto = A/(A+O);
tasa de falsa alarma = F/(A+F).

Entorno por defecto: pixi run python scripts/20_examen_sfincs_vs_satelite.py [modelos/sfincs-...]
Escribe: validacion/examen-<modelo>.png y .json
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import rasterio  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from util_sfincs import cota_subgrid_30m, nivel_maximo, niveles, profundidad_30m  # noqa: E402

MODELO = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("modelos/sfincs-bajo-piura")
HMIN = 0.10  # m
HORA_SATELITE = pd.Timestamp("2017-04-01 11:00")

with rasterio.open("validacion/s1_observado_30m.tif") as r:
    observado = r.read(1).astype(bool)
with rasterio.open("validacion/s1_evaluable_30m.tif") as r:
    evaluable = r.read(1).astype(bool)

cota = cota_subgrid_30m(MODELO)
mapa, tiempos = niveles(MODELO)


def examen(zs: np.ndarray, nombre: str) -> dict:
    profundidad = profundidad_30m(mapa, zs, cota)
    activo = np.isfinite(profundidad)
    simulado = np.nan_to_num(profundidad, nan=0) >= HMIN
    zona = evaluable & activo
    a = int((simulado & observado & zona).sum())
    o = int((~simulado & observado & zona).sum())
    f = int((simulado & ~observado & zona).sum())
    km2 = 0.0009  # un píxel de 30 m
    resultado = {
        "momento": nombre, "aciertos_km2": round(a * km2, 1), "omisiones_km2": round(o * km2, 1),
        "falsas_alarmas_km2": round(f * km2, 1), "CSI": round(a / max(a + o + f, 1), 3),
        "tasa_acierto": round(a / max(a + o, 1), 3), "tasa_falsa_alarma": round(f / max(a + f, 1), 3),
        "simulado_total_km2": round(float((simulado & activo).sum()) * km2, 1),
    }
    resultado["_categorias"] = np.where(~zona, 0, np.where(simulado & observado, 1,
                                        np.where(observado, 2, np.where(simulado, 3, 4))))
    return resultado


i_sat = int(np.argmin(np.abs(tiempos - HORA_SATELITE)))
resultados = [examen(mapa["zs"].isel(time=i_sat).values, f"a la hora del satélite ({tiempos[i_sat]:%d-%b %H:%M} UTC)"),
              examen(nivel_maximo(mapa), "máximo del evento")]

for r in resultados:
    print(f"{r['momento']}: CSI {r['CSI']:.2f} · acierto {r['tasa_acierto']:.0%} · falsa alarma {r['tasa_falsa_alarma']:.0%} "
          f"· aciertos {r['aciertos_km2']} km², omisiones {r['omisiones_km2']} km², falsas alarmas {r['falsas_alarmas_km2']} km²")

nombre = MODELO.name
Path(f"validacion/examen-{nombre}.json").write_text(json.dumps(
    {"modelo": nombre, "umbral_profundidad_m": HMIN,
     "resultados": [{k: v for k, v in r.items() if not k.startswith("_")} for r in resultados]},
    indent=2, ensure_ascii=False), encoding="utf-8")

colores = ListedColormap(["#f2f2f2", "#1f6fff", "#d62728", "#ff9f1c", "#ffffff"])
fig, ejes = plt.subplots(1, 2, figsize=(12, 9), constrained_layout=True)
for eje, r in zip(ejes, resultados):
    eje.imshow(r["_categorias"], cmap=colores, vmin=0, vmax=4, interpolation="nearest")
    eje.set_title(f"{r['momento']}\nCSI {r['CSI']:.2f} · acierto {r['tasa_acierto']:.0%}", fontsize=10)
    eje.set_axis_off()
leyenda = [plt.Rectangle((0, 0), 1, 1, color=c) for c in ["#1f6fff", "#d62728", "#ff9f1c", "#f2f2f2"]]
fig.legend(leyenda, ["Acierto: los dos ven agua", "Omisión: solo el satélite ve agua",
                     "Falsa alarma: solo el modelo pone agua", "No evaluable (ciudad, laderas, fuera del modelo)"],
           loc="lower center", ncol=2, fontsize=9)
fig.suptitle(f"El examen: SFINCS vs. Sentinel-1 — Bajo Piura, Niño Costero 2017 ({nombre})", fontsize=12)
fig.savefig(f"validacion/examen-{nombre}.png", dpi=110)
print(f"Figura: validacion/examen-{nombre}.png")
