# 02 — Fuentes de datos

Regla: **avisar el tamaño antes de descargar** y probar primero con un recorte chico. Los tamaños son estimados para la cuenca del Piura (~12,000 km²) y se confirman en la Fase 1.

## Globales (la base)

| Dato | Fuente | Para qué | Cuenta | Peso estimado (cuenca) |
|---|---|---|---|---|
| Relieve sin edificios ni árboles | **FABDEM** (30 m) | Inundación (SFINCS) | No | < 1 GB |
| Relieve + red de ríos | **MERIT Hydro** | Delimitar cuenca, Wflow | Registro gratis | < 1 GB |
| Relieve alternativo | Copernicus DEM GLO-30 | Contraste | No | < 1 GB |
| Lluvia reanálisis | **ERA5 / ERA5-Land** (Copernicus CDS) | Forzar Wflow | Sí (CDS) | Cientos de MB para 4 meses |
| Lluvia satelital | **GPM IMERG** (NASA) | Lluvia de mejor resolución | Sí (Earthdata) | Cientos de MB a pocos GB |
| Lluvia diaria | CHIRPS | Contraste | No | Bajo |
| Viviendas | **Google Open Buildings** | Impacto (FIAT) | No | Cientos de MB |
| Viviendas alternativas | Microsoft Building Footprints, OpenStreetMap | Contraste | No | Bajo |
| Población | **WorldPop**, GHSL | Personas expuestas | No | Bajo |
| Colegios, salud, vías | OpenStreetMap | Infraestructura crítica | No | Bajo |
| Uso y tipo de suelo | ESA WorldCover, SoilGrids | Wflow, rugosidad | No | Bajo |
| Inundación observada | **Sentinel-1** (radar) vía Google Earth Engine | Validación (Fase 3) | Sí (GEE) | Se procesa en la nube |
| Mapas de emergencia 2017 | Copernicus EMS, UNOSAT | Validación cruzada | No | Bajo |

## Locales (Perú)

| Dato | Fuente | Para qué | Nota |
|---|---|---|---|
| Lluvia en grilla | **PISCO** (SENAMHI) | Mejor lluvia que lo global para Perú | Pública; verificar acceso a la versión diaria |
| Caudal observado | SENAMHI / ANA, estación **Puente Sánchez Cerro** | Validar Wflow (Fase 2) | Puede requerir solicitud; buscar también en informes técnicos de 2017 |
| Daños 2017 | INDECI (SINPAD), informes de la Reconstrucción | Comparar impacto (Fase 4) | Reportes públicos |
| Peligros y riesgo | SIGRID (CENEPRED), GEOCATMIN (INGEMMET) | Comparar con lo "oficial" | Solo referencia |
| Estudios de la Reconstrucción | ARCC / convenio con Reino Unido (soluciones integrales en ríos) | Posible fuente de topografía y caudales de diseño | Verificar qué es público |

## Credenciales
Las cuentas (CDS, Earthdata, GEE) generan claves o tokens. Van en `.env` (ignorado por git) o en el archivo que cada librería espera en el perfil del usuario (por ejemplo `~/.cdsapirc`), **nunca** dentro del repo.
