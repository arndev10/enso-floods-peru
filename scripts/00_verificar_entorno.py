"""Verifica que el entorno de la Fase 0 esté completo.

Lee: nada. Escribe: nada. Solo imprime la versión de cada librería clave
y avisa cuál falta.
"""
import importlib

LIBRERIAS = [
    "hydromt",
    "hydromt_sfincs",
    "hydromt_wflow",
    "hydromt_fiat",
    "xarray",
    "rasterio",
    "geopandas",
    "cdsapi",
    "ee",
]

faltan = []
for nombre in LIBRERIAS:
    try:
        modulo = importlib.import_module(nombre)
        print(f"OK     {nombre:16} {getattr(modulo, '__version__', '?')}")
    except Exception as error:  # noqa: BLE001 - queremos ver cualquier fallo de import
        faltan.append(nombre)
        print(f"FALTA  {nombre:16} {error}")

print()
print("Entorno completo." if not faltan else f"Faltan: {', '.join(faltan)}")
