"""Compara la corrida local del ejemplo oficial de SFINCS con el resultado publicado por Deltares.

Lee: modelos/ejemplo-sfincs-compound/sfincs_map.nc (corrida local, Docker)
     modelos/ejemplo-sfincs-compound/referencia/sfincs_map.nc (resultado oficial)
Escribe: validacion/fase0-ejemplo-sfincs.png
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import xarray as xr  # noqa: E402

CARPETA = Path("modelos/ejemplo-sfincs-compound")
UMBRAL_MOJADO = 0.05  # m: profundidad mínima para contar una celda como inundada


def profundidad_maxima(ruta: Path) -> np.ndarray:
    with xr.open_dataset(ruta) as ds:
        zsmax = ds["zsmax"].max("timemax") if "timemax" in ds["zsmax"].dims else ds["zsmax"]
        return (zsmax - ds["zb"]).values


local = profundidad_maxima(CARPETA / "sfincs_map.nc")
oficial = profundidad_maxima(CARPETA / "referencia" / "sfincs_map.nc")

diferencia = np.abs(local - oficial)
mojado_local = local > UMBRAL_MOJADO
mojado_oficial = oficial > UMBRAL_MOJADO
aciertos = np.sum(mojado_local & mojado_oficial)
csi = aciertos / np.sum(mojado_local | mojado_oficial)

print(f"Celdas inundadas  local: {mojado_local.sum()}  oficial: {mojado_oficial.sum()}")
print(f"Diferencia máxima de profundidad: {np.nanmax(diferencia):.4f} m")
print(f"Diferencia media de profundidad:  {np.nanmean(diferencia):.4f} m")
print(f"CSI local vs oficial: {csi:.3f}  (1.0 = idénticos)")

fig, ejes = plt.subplots(1, 3, figsize=(15, 4.5), constrained_layout=True)
for eje, datos, titulo in (
    (ejes[0], np.where(mojado_oficial, oficial, np.nan), "Resultado oficial de Deltares"),
    (ejes[1], np.where(mojado_local, local, np.nan), "Corrida local (Docker)"),
):
    imagen = eje.imshow(datos, origin="lower", cmap="Blues", vmin=0, vmax=2)
    eje.set_title(titulo)
    eje.set_axis_off()
fig.colorbar(imagen, ax=ejes[:2], label="Profundidad máxima (m)", shrink=0.8)
imagen = ejes[2].imshow(diferencia, origin="lower", cmap="Reds", vmin=0, vmax=0.05)
ejes[2].set_title(f"Diferencia absoluta (CSI = {csi:.3f})")
ejes[2].set_axis_off()
fig.colorbar(imagen, ax=ejes[2], label="m", shrink=0.8)
fig.suptitle("Fase 0 — ejemplo oficial de SFINCS (sfincs_compound)")

salida = Path("validacion/fase0-ejemplo-sfincs.png")
fig.savefig(salida, dpi=110)
print(f"Figura: {salida}")
