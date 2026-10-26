"""Sensibilidad de Wflow: qué parámetros mueven el pico en Sánchez Cerro, probando 2017 y 1998 a la vez.

Con lluvia ERA5-Land el modelo sin calibrar exagera de forma sistemática (×1.6 en 2017, ×2.1 en 1998).
Se prueban ajustes con sentido físico, sin rearmar el modelo (Wflow 1.0 acepta `scale` sobre mapas y
cambios de constantes en el TOML). Cada variante se escribe como un TOML aparte con su propia carpeta
de salida, y todas corren en una sola sesión de Julia.

Entorno wflow: pixi run -e wflow python scripts/24_sensibilidad_wflow.py [variante ...]
(sin argumentos corre todas; las ya corridas se leen de su carpeta sens_<variante>/)
Lee: modelos/wflow-piura-era5land/, modelos/wflow-piura-1998/ (y modelos/wflow-piura/ para IMERG).
Escribe: validacion/sensibilidad-wflow.csv
"""
import re
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

OBSERVADO = {"2017": 3468, "1998": 4424}  # m³/s en Sánchez Cerro (COEN-INDECI 2017; máximo histórico 1998)
MODELOS = {"2017": Path("modelos/wflow-piura-era5land"), "1998": Path("modelos/wflow-piura-1998")}

# nombre → (constantes a cambiar, mapas a escalar)
VARIANTES = {
    "base": ({}, {}),
    "perdida_profunda_5": ({"soil_water_saturated_zone_bottom__max_leakage_volume_flux": 5}, {}),
    "perdida_profunda_20": ({"soil_water_saturated_zone_bottom__max_leakage_volume_flux": 20}, {}),
    "perdida_profunda_30": ({"soil_water_saturated_zone_bottom__max_leakage_volume_flux": 30}, {}),
    "perdida_profunda_35": ({"soil_water_saturated_zone_bottom__max_leakage_volume_flux": 35}, {}),
    "perdida_profunda_50": ({"soil_water_saturated_zone_bottom__max_leakage_volume_flux": 50}, {}),
    "flujo_lateral_x5": ({"subsurface_water__horizontal_to_vertical_saturated_hydraulic_conductivity_ratio": 500}, {}),
    "suelo_x1.5": ({}, {"soil__thickness": ("soil_thickness", 1.5)}),
    "rio_rugoso_x2": ({}, {"river_water_flow__manning_n_parameter": ("river_manning_n", 2.0)}),
}


def escribir_variante(modelo: Path, nombre: str, constantes: dict, mapas: dict) -> Path:
    texto = (modelo / "wflow_sbm.toml").read_text(encoding="utf-8")
    texto = re.sub(r'^dir_output = ".*"$', f'dir_output = "sens_{nombre}"', texto, count=1, flags=re.M)
    for clave, valor in constantes.items():
        texto, n = re.subn(rf"(\[input\.static\.{re.escape(clave)}\]\s*\nvalue = )[^\n]+", rf"\g<1>{valor}", texto)
        if n == 0:
            raise SystemExit(f"No encontré la constante {clave} en el TOML")
    for clave, (variable, factor) in mapas.items():
        texto, n = re.subn(rf'^{re.escape(clave)} = "{variable}"\n', "", texto, flags=re.M)
        if n == 0:
            raise SystemExit(f"No encontré el mapa {clave} en el TOML")
        texto += f'\n[input.static.{clave}]\nnetcdf_variable_name = "{variable}"\nscale = {factor}\n'
    ruta = modelo / f"sens_{nombre}.toml"
    ruta.write_text(texto, encoding="utf-8")
    return ruta


elegidas = sys.argv[1:] or list(VARIANTES)
tomls = [escribir_variante(m, n, *VARIANTES[n]) for n in elegidas for m in MODELOS.values()]
inicio = time.time()
comando = "using Wflow; for f in ARGS; Wflow.run(f; silent=true); end"
resultado = subprocess.run(["julia", "--project=julia", "-e", comando, *[str(t.resolve()) for t in tomls]],
                           capture_output=True, text=True)
if resultado.returncode != 0:
    print(resultado.stderr[-3000:])
    raise SystemExit("Falló una corrida de Wflow")
print(f"{len(tomls)} corridas en {time.time() - inicio:.0f} s")

filas = []
for nombre in [v for v in VARIANTES if all((m / f"sens_{v}" / "output.csv").exists() for m in MODELOS.values())]:
    fila = {"variante": nombre}
    for anio, modelo in MODELOS.items():
        serie = pd.read_csv(modelo / f"sens_{nombre}" / "output.csv", parse_dates=["time"], index_col="time")
        serie = serie.filter(like="river_q").iloc[:, 0]
        fila[f"pico_{anio}"] = round(serie.max())
        fila[f"ratio_{anio}"] = round(serie.max() / OBSERVADO[anio], 2)
        fila[f"fecha_{anio}"] = f"{serie.idxmax():%d-%b}"
    filas.append(fila)
tabla = pd.DataFrame(filas)
tabla["error_medio_%"] = ((tabla["ratio_2017"] - 1).abs() + (tabla["ratio_1998"] - 1).abs()) / 2 * 100
tabla.to_csv("validacion/sensibilidad-wflow.csv", index=False)
print(tabla.round(1).to_string(index=False))
print("Observado: 2017 = 3,468 m³/s (27-mar) · 1998 = 4,424 m³/s")
