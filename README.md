# Piura 2017: la inundación del Niño Costero simulada con software abierto

Reconstrucción de la inundación del río Piura (Niño Costero, marzo de 2017) con el software abierto de **Deltares** (Países Bajos), **solo con datos públicos y globales**, validada contra satélite (radar Sentinel-1 y Landsat 8).

> ⚠️ **Demostración técnica. No es un pronóstico oficial.** Sigue siempre los avisos de INDECI, SENAMHI y el ENFEN.

Proyecto personal y sin fines de lucro de Arnold Torres Larriega (ingeniero industrial, PMP), hecho con apoyo de inteligencia artificial (Claude Code). No soy hidrólogo: si eres especialista y ves algo mal planteado, abre un *issue*. Esa revisión es justamente lo que busco.

Explicación en video (divulgación): https://youtu.be/lE9HPCi1ZLE

## Resultados en una tabla

| Pregunta | Resultado |
|---|---|
| ¿El modelo de cuenca (Wflow) llega al pico? | 3,252 m³/s frente a 3,468 m³/s oficiales (94%), pero **4 días tarde** |
| ¿La mancha simulada (SFINCS) coincide con el satélite? | CSI **0.50** contra radar + Landsat (0.31 solo contra radar) |
| ¿Por qué el radar castiga al modelo? | ~**48%** de sus "falsas alarmas" eran agua real en Landsat (agua entre cultivos que el radar no ve) |
| Exposición con ≥ 60 cm de agua | ~50,900 edificios y ~160,800 personas (edificios de hoy, población 2017) |

Detalle completo, método y limitaciones: **[NOTA-TECNICA.md](NOTA-TECNICA.md)**.

![Examen del modelo final contra el radar](validacion/examen-sfincs-final.png)

## Stack

- **Wflow** (Julia 1.0.4) para la cuenca, armado con **HydroMT** (`hydromt_wflow` 1.1).
- **SFINCS** (Docker `deltares/sfincs-cpu`) para la inundación del Bajo Piura, armado con `hydromt_sfincs`.
- **Google Earth Engine** para Sentinel-1, Landsat 8, IMERG, ERA5-Land, MERIT Hydro, SoilGrids y WorldCover.
- Entorno reproducible con **pixi** (`pixi.toml` + `pixi.lock`).

## Cómo reproducirlo

1. `pixi install` (entorno por defecto: SFINCS) y `pixi install -e wflow` (entorno de Wflow).
2. Copia `.env.example` a `.env` y llena tus propias claves (Copernicus CDS, NASA Earthdata y el ID de tu proyecto de Earth Engine). **El `.env` nunca se sube.**
3. `pixi run verificar` para comprobar el entorno.
4. Corre los scripts en orden numérico (`pixi run python scripts/NN_*.py`, o `pixi run -e wflow ...` para los de Wflow). Cada script dice en su cabecera qué lee y qué escribe.

Las descargas (`datos/`) y los modelos (`modelos/`) pesan varios GB y no se versionan: se regeneran con los scripts. En `validacion/` quedan las métricas, figuras y animaciones.

```
config/      recetas de HydroMT para Wflow (2017, 1998, lluvia alternativa)
geo/         cuenca, estaciones e infraestructura (OSM) en GeoJSON
scripts/     pipeline completo, de 00 (entorno) a 29 (gráfico final)
validacion/  exámenes contra satélite, impacto, sensibilidad, animaciones
web/         comparador antes/después con barra deslizable (abrir index.html)
docs/        stack de Deltares, fuentes de datos y nota de SFINCS en Docker
julia/       proyecto Julia con Wflow 1.0.4
```

## Licencias

- **Código** (`scripts/`, `config/`, `web/`): [MIT](LICENSE).
- **Textos, figuras y resultados** (`docs/`, `NOTA-TECNICA.md`, `validacion/`): [CC BY 4.0](LICENSE-CC-BY-4.0.md). Puedes reutilizarlos citando la fuente.
- **Datos de terceros:** conservan su propia licencia. Los GeoJSON `geo/osm-*` son © colaboradores de OpenStreetMap ([ODbL](https://opendatacommons.org/licenses/odbl/)); las imágenes Sentinel-1 contienen datos Copernicus modificados (ESA, 2017); Landsat 8 es cortesía de NASA/USGS. Las demás fuentes y sus créditos están en [docs/02-fuentes-de-datos.md](docs/02-fuentes-de-datos.md).

## Agradecimientos

A **Deltares** y a los Países Bajos por publicar Wflow, SFINCS y HydroMT como software abierto. Al trabajo de Farías et al. (LACCEI 2020) sobre el pronóstico de caudales del río Piura y al de Reyes y Terrones (LACCEI 2020) sobre la medición del pico de 2017.

---

### English summary

Open reconstruction of the 2017 Coastal El Niño flood of the Piura river (Peru) using Deltares' open-source stack (Wflow + SFINCS + HydroMT) and only global/public data. The basin model reaches 94% of the official peak (3,252 vs 3,468 m³/s) but 4 days late. The flood extent scores CSI 0.50 against a combined Sentinel-1 + Landsat 8 reference, and about half of the radar "false alarms" turned out to be real water hidden under crops. This is a technical demonstration, not an official forecast. Feedback from hydrologists is very welcome: please open an issue. Code under MIT, results under CC BY 4.0.
