"""Baja el caudal diario de GloFAS (reanálisis LISFLOOD v5) de enero a abril de 2017 cerca de Piura.

GloFAS vive en el portal EWDS de Copernicus (no en CDS). Usa la misma clave CDSAPI_KEY.
Sirve como referencia del caudal de 2017 mientras no tengamos la serie observada de
Sánchez Cerro, y para comparar con lo que simule Wflow.

Lee: CDSAPI_KEY del .env. Escribe: datos/caudal/glofas_piura_2017-01a04.nc (no va a git).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
import cdsapi  # noqa: E402

salida = Path("datos/caudal/glofas_piura_2017-01a04.nc")
salida.parent.mkdir(parents=True, exist_ok=True)

cliente = cdsapi.Client(url="https://ewds.climate.copernicus.eu/api", key=os.environ["CDSAPI_KEY"], quiet=True, progress=False)
cliente.retrieve(
    "cems-glofas-historical",
    {
        "system_version": ["version_5_0"],
        "hydrological_model": ["lisflood"],
        "product_type": ["consolidated"],
        "timespan": ["time_mean"],
        "variable": ["average_river_discharge_in_the_last_24_hours"],
        "year": ["2017"],
        "month": ["01", "02", "03", "04"],
        "day": [f"{d:02d}" for d in range(1, 32)],
        "area": [-5.0, -80.8, -5.4, -80.4],  # norte, oeste, sur, este: ciudad de Piura
        "data_format": "netcdf",
        "download_format": "unarchived",
    },
    str(salida),
)
print(f"GloFAS → {salida} ({salida.stat().st_size / 1e6:.2f} MB)")
