"""Animación de la inundación simulada por SFINCS, pensada para el público (videos y shorts).

Cada cuadro tiene:
  - mapa: relieve sombreado de FABDEM + profundidad del agua (≥ 10 cm) con colores en escala
    humana (tobillo, rodilla, cintura, pecho, sobre la cabeza); el mar en un color propio;
  - fecha y hora de Perú;
  - mini gráfico del caudal del río con un punto que avanza y la línea del umbral de inundación
    de la ciudad (~1,900 m³/s);
  - el aviso "demostración técnica, no aviso oficial".

Entorno por defecto: pixi run python scripts/25_animacion_inundacion.py [modelos/sfincs-...] [--vertical]
  --vertical: 1080×1920 (shorts/reels). Sin la opción: 1920×1080 (YouTube).
Escribe: <modelo>/animacion[-vertical]/cuadro_XXXX.png y validacion/animacion-<modelo>[-vertical].mp4
"""
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import BoundaryNorm, LightSource, ListedColormap  # noqa: E402
from scipy import ndimage  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from util_sfincs import cota_subgrid_30m, niveles, profundidad_30m  # noqa: E402

argumentos = [a for a in sys.argv[1:] if not a.startswith("--")]
MODELO = Path(argumentos[0]) if argumentos else Path("modelos/sfincs-bajo-piura-inf")
VERTICAL = "--vertical" in sys.argv
CADA_HORAS = 3
DESDE = pd.Timestamp("2017-03-20")
UMBRAL_CIUDAD = 1900  # m³/s a partir del cual el río inunda la ciudad
SUFIJO = "-vertical" if VERTICAL else ""
CARPETA = MODELO / f"animacion{SUFIJO}"
CARPETA.mkdir(exist_ok=True)
for viejo in CARPETA.glob("cuadro_*.png"):
    viejo.unlink()

FONDO, TEXTO, SUAVE, MAR = "#0f1317", "#f2f2f2", "#a9b0b8", "#2b3f52"
# Escala humana: tobillo, rodilla, cintura, pecho, sobre la cabeza
LIMITES = [0.10, 0.30, 0.60, 1.20, 1.80, 10.0]
ETIQUETAS = ["tobillo\n10–30 cm", "rodilla\n30–60 cm", "cintura\n0.6–1.2 m", "pecho\n1.2–1.8 m", "sobre la\ncabeza"]
COLORES = ListedColormap(["#bfe3ff", "#7cc0f5", "#3b8fe0", "#1f5cb8", "#0b2f73"])
NORMA = BoundaryNorm(LIMITES, COLORES.N)

cota = cota_subgrid_30m(MODELO)
mapa, tiempos = niveles(MODELO)
caudal = pd.read_csv(MODELO / "sfincs.dis", sep=r"\s+", header=None, names=["seg", "q"])
tref = next(l.split("=")[1].strip() for l in (MODELO / "sfincs.inp").read_text().splitlines() if l.startswith("tref"))
caudal.index = pd.to_datetime(tref, format="%Y%m%d %H%M%S") + pd.to_timedelta(caudal["seg"], unit="s")
caudal_peru = caudal["q"].copy()
caudal_peru.index = caudal_peru.index - pd.Timedelta(hours=5)

# Recorte al área activa del modelo (sin el tablazo vacío a los costados)
activo = np.isfinite(profundidad_30m(mapa, mapa["zs"].isel(time=0).values, cota))
filas, columnas = np.where(activo)
f0, f1, c0, c1 = filas.min(), filas.max() + 1, columnas.min(), columnas.max() + 1
cota_r = cota[f0:f1, c0:c1]
# Mar = zona baja (≤ 0.5 m) CONECTADA al borde oeste. La depresión de Sechura también está bajo el
# nivel del mar, pero tierra adentro: ahí se forma la laguna y debe verse como inundación.
bajo = ~np.isfinite(cota_r) | (cota_r <= 0.5)
etiquetas, _ = ndimage.label(bajo)
ids_oeste = np.unique(etiquetas[:, 0][etiquetas[:, 0] > 0])
mar = np.isin(etiquetas, ids_oeste)
relieve = np.where(np.isfinite(cota_r), np.maximum(cota_r, 0), 0)
sombra = LightSource(azdeg=315, altdeg=40).hillshade(relieve, vert_exag=8, dx=30, dy=30)
sombra = np.where(mar, np.nan, sombra)
capa_mar = np.where(mar, 1.0, np.nan)


def armar_lienzo():
    if VERTICAL:
        fig = plt.figure(figsize=(10.8, 19.2), dpi=100, facecolor=FONDO)
        eje_mapa = fig.add_axes([0.03, 0.15, 0.94, 0.62])
        eje_q = fig.add_axes([0.12, 0.045, 0.82, 0.075], facecolor=FONDO)
        eje_ley = fig.add_axes([0.06, 0.795, 0.88, 0.018])
        texto = {"titulo": (0.05, 0.978, 30), "fecha": (0.05, 0.905, 26), "q": (0.05, 0.873, 20), "aviso": (0.05, 0.012, 13)}
    else:
        fig = plt.figure(figsize=(19.2, 10.8), dpi=100, facecolor=FONDO)
        eje_mapa = fig.add_axes([0.45, 0.02, 0.53, 0.96])
        eje_q = fig.add_axes([0.05, 0.12, 0.36, 0.25], facecolor=FONDO)
        eje_ley = fig.add_axes([0.05, 0.50, 0.36, 0.03])
        texto = {"titulo": (0.05, 0.93, 28), "fecha": (0.05, 0.76, 34), "q": (0.05, 0.68, 22), "aviso": (0.05, 0.03, 13)}
    return fig, eje_mapa, eje_q, eje_ley, texto


indices = [i for i, t in enumerate(tiempos) if t >= DESDE and (t - DESDE) % pd.Timedelta(hours=CADA_HORAS) == pd.Timedelta(0)]
for n, i in enumerate(indices):
    h = profundidad_30m(mapa, mapa["zs"].isel(time=i).values, cota)[f0:f1, c0:c1]
    h = np.where((h >= 0.10) & ~mar, h, np.nan)
    ahora_peru = tiempos[i] - pd.Timedelta(hours=5)
    q = float(caudal_peru.reindex([ahora_peru], method="nearest").iloc[0])

    fig, eje_mapa, eje_q, eje_ley, texto = armar_lienzo()
    eje_mapa.imshow(capa_mar, cmap=ListedColormap([MAR]), vmin=0, vmax=1, interpolation="nearest")
    eje_mapa.imshow(sombra, cmap="gray", vmin=0.15, vmax=1, interpolation="bilinear")
    eje_mapa.imshow(h, cmap=COLORES, norm=NORMA, interpolation="nearest")
    eje_mapa.set_axis_off()

    x, y, tam = texto["titulo"]
    fig.text(x, y, "Inundación del Bajo Piura\nNiño Costero 2017", color=TEXTO, fontsize=tam, weight="bold",
             va="top", linespacing=1.15)
    x, y, tam = texto["fecha"]
    fecha = f"{ahora_peru.day} de {'marzo' if ahora_peru.month == 3 else 'abril'} · {ahora_peru:%H:%M} h"
    fig.text(x, y, fecha, color=TEXTO, fontsize=tam, va="top")
    x, y, tam = texto["q"]
    color_q = "#ff6b5a" if q >= UMBRAL_CIUDAD else SUAVE
    fig.text(x, y, f"Caudal del río: {q:,.0f} m³/s", color=color_q, fontsize=tam, va="top")
    x, y, tam = texto["aviso"]
    fig.text(x, y, "Simulación SFINCS (Deltares) con datos públicos · demostración técnica, no aviso oficial",
             color=SUAVE, fontsize=tam)

    # Leyenda en escala humana
    eje_ley.imshow(np.arange(5)[None, :], cmap=COLORES, aspect="auto")
    eje_ley.set_xticks(range(5), ETIQUETAS, color=TEXTO, fontsize=12 if VERTICAL else 13)
    eje_ley.set_yticks([])
    eje_ley.tick_params(length=0)
    for borde in eje_ley.spines.values():
        borde.set_visible(False)
    eje_ley.set_title("¿Hasta dónde llega el agua?", color=TEXTO, fontsize=16, loc="left")

    # Mini gráfico del caudal
    serie = caudal_peru[DESDE - pd.Timedelta(hours=5):]
    eje_q.plot(serie.index, serie.values, color="#5fa8ff", linewidth=2)
    eje_q.axhline(UMBRAL_CIUDAD, color="#ff6b5a", linestyle="--", linewidth=1.2)
    eje_q.text(serie.index[0], UMBRAL_CIUDAD + 120, " desde aquí se inunda la ciudad (~1,900 m³/s)", color="#ff6b5a",
               fontsize=11, va="bottom")
    eje_q.scatter([ahora_peru], [q], color="white", s=60, zorder=5)
    eje_q.set_ylabel("m³/s", color=SUAVE)
    eje_q.tick_params(colors=SUAVE, labelsize=10)
    eje_q.set_ylim(0, max(serie.max() * 1.1, 4000))
    for lado in ("top", "right"):
        eje_q.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        eje_q.spines[lado].set_color(SUAVE)
    eje_q.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d-%m"))

    fig.savefig(CARPETA / f"cuadro_{n:04d}.png", facecolor=FONDO)
    plt.close(fig)
print(f"{len(indices)} cuadros en {CARPETA}")

video = Path(f"validacion/animacion-{MODELO.name}{SUFIJO}.mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "8", "-i", str(CARPETA / "cuadro_%04d.png"),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(video)], check=True)
print(f"Video: {video} ({video.stat().st_size / 1e6:.1f} MB)")
