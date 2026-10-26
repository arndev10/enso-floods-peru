"""Baja de Earth Engine las capas estáticas que necesita Wflow, alineadas a su rejilla original.

- MERIT Hydro v1.0.1 (3″ ≈ 90 m): elv, dir, upa, upg, wth, hnd.
- SoilGrids 2.0 de ISRIC (7.5″ ≈ 250 m): bdod, clay, silt, sand, soc, phh2o en 6 profundidades.
- MODIS MCD15A3H v6.1 (15″ ≈ 500 m): LAI, climatología mensual 2010-2020.
- ESA WorldCover 2021 (a 3″, para toda la cuenca).

Lee: GEE_PROJECT del .env. Escribe: datos/wflow/crudo_gee/*.tif (no van a git).
Recuadro: lon -81.25 a -79.25, lat -6.25 a -4.5 (cuenca del Piura con margen).
"""
import os
import urllib.error
import urllib.request
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)

import ee  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv()
ee.Initialize(project=os.environ["GEE_PROJECT"])

OESTE, ESTE, SUR, NORTE = -81.25, -79.25, -6.25, -4.5
CARPETA = Path("datos/wflow/crudo_gee")
CARPETA.mkdir(parents=True, exist_ok=True)


def bajar(imagen: ee.Image, nombre: str, celdas_por_grado: int) -> None:
    """Descarga `imagen` en una rejilla EPSG:4326 exacta de 1/celdas_por_grado grados."""
    salida = CARPETA / f"{nombre}.tif"
    if salida.exists():
        print(f"  {nombre:22} ya existe")
        return
    res = 1 / celdas_por_grado
    ancho = round((ESTE - OESTE) * celdas_por_grado)
    alto = round((NORTE - SUR) * celdas_por_grado)
    url = imagen.getDownloadURL(
        {
            "crs": "EPSG:4326",
            "crs_transform": [res, 0, OESTE, 0, -res, NORTE],
            "dimensions": f"{ancho}x{alto}",
            "format": "GEO_TIFF",
        }
    )
    try:
        urllib.request.urlretrieve(url, salida)
    except urllib.error.HTTPError as error:
        raise SystemExit(f"{nombre} falló: {error.read().decode()[:400]}")
    print(f"  {nombre:22} {ancho}x{alto} px  {salida.stat().st_size / 1e6:.1f} MB")


print("MERIT Hydro")
merit = ee.Image("MERIT/Hydro/v1_0_1")
for banda, tipo in (("elv", "toFloat"), ("upa", "toFloat"), ("wth", "toFloat"), ("hnd", "toFloat"),
                    ("upg", "toInt32"), ("dir", "toInt16")):
    relleno = -9 if banda == "dir" else -9999
    bajar(getattr(merit.select(banda).unmask(relleno), tipo)(), f"merit_{banda}", 1200)

print("SoilGrids 2.0")
profundidades = ["0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm", "100-200cm"]
for variable in ("bdod", "clay", "silt", "sand", "soc", "phh2o"):
    imagen = ee.Image(f"projects/soilgrids-isric/{variable}_mean")
    bandas = [f"{variable}_{p}_mean" for p in profundidades]
    bajar(imagen.select(bandas).unmask(-1).toFloat(), f"soilgrids_{variable}", 480)

print("MODIS LAI")
lai = ee.ImageCollection("MODIS/061/MCD15A3H").filterDate("2010-01-01", "2021-01-01").select("Lai")
meses = []
for mes in range(1, 13):
    del_mes = lai.filter(ee.Filter.calendarRange(mes, mes, "month"))
    # Valores > 100 son códigos de relleno (agua, sin dato); escala 0.1 → LAI real
    meses.append(del_mes.map(lambda i: i.updateMask(i.lte(100))).mean().multiply(0.1).rename(f"lai_{mes:02d}"))
bajar(ee.Image.cat(meses).unmask(0).toFloat(), "modis_lai_clim", 240)

print("ESA WorldCover (toda la cuenca)")
# La capa de datos/exposicion/ solo cubre el dominio de inundación del Bajo Piura; Wflow necesita
# toda la cuenca. Vecino más cercano a la rejilla de MERIT (3″): las clases no se promedian.
bajar(ee.ImageCollection("ESA/WorldCover/v200").first().select("Map").unmask(0).toUint8(),
      "esa_worldcover", 1200)
