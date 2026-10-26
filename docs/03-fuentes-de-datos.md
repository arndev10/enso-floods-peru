# 02 · Fuentes de datos usadas y sus licencias

Todas son públicas y gratuitas. Cada una conserva su licencia. Si reutilizas los resultados, cita también las fuentes.

| Dato | Fuente | Uso aquí | Script | Licencia / crédito |
|---|---|---|---|---|
| Relieve sin edificios ni árboles (30 m) | **FABDEM** v1-2 (Hawker et al., 2022; Universidad de Bristol y Fathom) | Relieve de SFINCS | 06 | **CC BY-NC-SA 4.0 (no comercial)** |
| Hidrografía (90 m) | **MERIT Hydro** (Yamazaki et al., 2019) | Cuenca y red de Wflow | 11, 12 | **CC BY-NC 4.0 u ODbL 1.0** |
| Ríos con ancho y Q2 | Lin et al. (2019), red global de ríos sobre MERIT | Ríos de Wflow | 13 | **Uso no comercial** (ver la fuente) |
| Cuencas | HydroBASINS nivel 12 (HydroSHEDS, WWF) | Delimitar la cuenca | 04 | Licencia HydroSHEDS, con atribución |
| Pendiente (máscara del radar) | Copernicus DEM GLO-30 | Excluir laderas | 05, 19 | © DLR e.V. y © Airbus, provisto bajo COPERNICUS por la UE y la ESA |
| Suelos | SoilGrids 2.0 (ISRIC) | Parámetros de suelo de Wflow | 11 | CC BY 4.0 |
| Cobertura del suelo | ESA WorldCover 2021 | Wflow y rugosidad de SFINCS | 07, 11 | CC BY 4.0 |
| Índice de área foliar | MODIS MCD15A2H (NASA) | Vegetación de Wflow | 11 | Datos NASA, sin restricción de uso |
| Lluvia satelital | GPM IMERG V07 (NASA) | Lluvia de Wflow y SFINCS | 14 | Datos NASA, sin restricción de uso |
| Clima reanálisis | ERA5-Land (Copernicus / ECMWF) | Lluvia alternativa, temperatura y evaporación de Wflow | 16 | Licencia Copernicus, con atribución |
| Caudal global | GloFAS v5 (Copernicus Emergency Management Service) | Referencia de caudal | 09 | Licencia CEMS, con atribución |
| Radar | Copernicus Sentinel-1 (ESA), vía Google Earth Engine | Mancha observada (examen) | 05, 19, 23 | Contiene datos Copernicus Sentinel modificados (2016-2017) |
| Óptico | Landsat 8 (NASA/USGS) y Sentinel-2 (ESA) | Segunda opinión del examen | 26 | Landsat: dominio público. Sentinel-2: datos Copernicus |
| Edificios | Google Open Buildings v3 | Exposición | 07 | CC BY 4.0 u ODbL 1.0 |
| Población | WorldPop 2017 | Exposición | 07 | CC BY 4.0 |
| Colegios, salud y vías | OpenStreetMap (oct-2026) | Exposición | 21 | © colaboradores de OpenStreetMap, ODbL |

**Respaldo no usado en la receta final:** ERA5 de Copernicus CDS (scripts 08 y 10).

## Consecuencia para los resultados

El relieve (FABDEM) y la hidrografía (MERIT Hydro y Lin et al.) se publican **solo para uso no comercial**. Los mapas de inundación, animaciones y cifras de exposición derivan de ellos, así que **su uso comercial no está permitido** sin revisar esas licencias. Este proyecto es sin fines de lucro.

## Datos locales del Perú

| Dato | Fuente | Estado |
|---|---|---|
| Pico de 2017 en Sánchez Cerro (3,468 m³/s, 27-mar 12:00) | COEN-INDECI | Usado como referencia |
| Serie horaria de caudal y nivel de Sánchez Cerro, curva de descarga | Proyecto Especial Chira-Piura (Gobierno Regional de Piura) | Solicitada por acceso a la información pública (oct-2026) |
| Lluvia en grilla PISCO | SENAMHI | No usada todavía |
| Daños de 2017 | INDECI (SINPAD) | Pendiente para contrastar la exposición |

Las licencias se transcriben de cada fuente a octubre de 2026. Ante la duda, manda la página oficial de cada conjunto de datos.
