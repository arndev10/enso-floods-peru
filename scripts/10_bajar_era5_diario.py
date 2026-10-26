"""Baja el clima diario de ERA5 para forzar Wflow (jul-2016 a may-2017: 6 meses de calentamiento + el evento).

Usa el producto de Copernicus "derived-era5-single-levels-daily-statistics" (medias diarias de
los valores horarios) y la orografía de ERA5. Deja todo en las unidades finales que espera
hydromt_wflow, así el catálogo no necesita conversiones:
  precip mm/día · temp °C · press_msl hPa · kin W/m² · elevtn (orografía) m.

Lee: CDSAPI_URL y CDSAPI_KEY del .env.
Escribe: datos/wflow/era5_diario_2016-07a2017-05.nc, datos/wflow/era5_orografia.nc (no van a git).
"""
from pathlib import Path

import xarray as xr
from dotenv import load_dotenv

load_dotenv()
import cdsapi  # noqa: E402

CARPETA = Path("datos/wflow")
CRUDO = CARPETA / "crudo_era5"
CRUDO.mkdir(parents=True, exist_ok=True)
AREA = [-4.5, -81.25, -6.25, -79.25]  # norte, oeste, sur, este (cuenca del Piura con margen)
PERIODOS = {"2016": [f"{m:02d}" for m in range(7, 13)], "2017": [f"{m:02d}" for m in range(1, 6)]}
VARIABLES = {
    "total_precipitation": "precip",
    "2m_temperature": "temp",
    "mean_sea_level_pressure": "press_msl",
    "surface_solar_radiation_downwards": "kin",
}
cliente = cdsapi.Client(quiet=True, progress=False)

# 1) Medias diarias, una petición por variable y año (peticiones chicas = menos espera en la cola)
for variable_cds in VARIABLES:
    for anio, meses in PERIODOS.items():
        salida = CRUDO / f"{variable_cds}_{anio}.nc"
        if salida.exists():
            continue
        cliente.retrieve(
            "derived-era5-single-levels-daily-statistics",
            {
                "product_type": "reanalysis",
                "variable": [variable_cds],
                "year": anio,
                "month": meses,
                "day": [f"{d:02d}" for d in range(1, 32)],
                "daily_statistic": "daily_mean",
                "time_zone": "utc-05:00",  # hora de Perú: el "día" coincide con el día local
                "frequency": "1_hourly",
                "area": AREA,
            },
            str(salida),
        )
        print(f"  {salida.name}")

# 2) Orografía (geopotencial de superficie, un solo instante)
orografia_crudo = CRUDO / "geopotencial.nc"
if not orografia_crudo.exists():
    cliente.retrieve(
        "reanalysis-era5-single-levels",
        {
            "product_type": ["reanalysis"],
            "variable": ["geopotential"],
            "year": ["2017"], "month": ["01"], "day": ["01"], "time": ["00:00"],
            "area": AREA,
            "data_format": "netcdf",
            "download_format": "unarchived",
        },
        str(orografia_crudo),
    )

# 3) Unir, renombrar y pasar a unidades finales
def abrir(variable_cds: str) -> xr.DataArray:
    ds = xr.open_mfdataset(sorted(CRUDO.glob(f"{variable_cds}_*.nc")), combine="by_coords")
    da = ds[list(ds.data_vars)[0]]
    return da.rename({"valid_time": "time"}) if "valid_time" in da.dims else da


clima = xr.Dataset(
    {
        "precip": abrir("total_precipitation") * 24 * 1000,  # media horaria [m] → total diario [mm]
        "temp": abrir("2m_temperature") - 273.15,  # K → °C
        "press_msl": abrir("mean_sea_level_pressure") / 100,  # Pa → hPa
        "kin": abrir("surface_solar_radiation_downwards") / 3600,  # J/m² por hora → W/m²
    }
)
clima = clima.drop_vars([c for c in clima.coords if c not in ("time", "latitude", "longitude")])
clima["precip"] = clima["precip"].clip(min=0)
clima.attrs = {"fuente": "ERA5 daily statistics (Copernicus CDS)", "unidades": "precip mm/d, temp C, press_msl hPa, kin W/m2"}
salida = CARPETA / "era5_diario_2016-07a2017-05.nc"
clima.load().to_netcdf(salida)
print(f"Clima → {salida} ({salida.stat().st_size / 1e6:.1f} MB), {clima.sizes['time']} días")

geo = xr.open_dataset(orografia_crudo)
elevtn = (geo["z"].squeeze(drop=True) / 9.80665).rename("elevtn")
elevtn = elevtn.drop_vars([c for c in elevtn.coords if c not in ("latitude", "longitude")])
elevtn.to_dataset().to_netcdf(CARPETA / "era5_orografia.nc")
print(f"Orografía → {CARPETA / 'era5_orografia.nc'}")
