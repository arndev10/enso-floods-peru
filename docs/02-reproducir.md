# Cómo reproducir la corrida final

Probado en **Windows 11** con Git Bash. El `pixi.toml` declara solo `win-64`. En Linux o macOS habría que agregar la plataforma y volver a resolver el entorno.

## Requisitos

- [pixi](https://pixi.sh) para los entornos de Python.
- [Julia](https://julialang.org) 1.13 (Wflow 1.0.4). Una vez: `julia --project=julia -e "using Pkg; Pkg.instantiate()"`.
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) para SFINCS (`deltares/sfincs-cpu`). Ver [05-sfincs-docker.md](05-sfincs-docker.md).
- Cuentas gratuitas: Google Earth Engine (con un proyecto de Cloud), Copernicus CDS/EWDS (para GloFAS) y NASA Earthdata (opcional: IMERG se baja por Earth Engine).
- Unos **10 GB** libres en disco para `datos/` y `modelos/`.

## Pasos

```bash
pixi install && pixi install -e wflow
cp .env.example .env          # llena tus claves; el .env nunca se sube
earthengine authenticate
pixi run verificar            # 00: comprueba el entorno
pixi run python scripts/01_probar_earth_engine.py
pixi run python scripts/02_probar_conexiones.py
```

**1. Cuenca, relieve, exposición y satélite** (entorno por defecto)

```bash
pixi run python scripts/04_delimitar_cuenca.py
pixi run python scripts/05_mancha_sentinel1.py
pixi run python scripts/06_bajar_relieve.py
pixi run python scripts/07_bajar_capas_exposicion.py
pixi run python scripts/09_bajar_glofas.py
pixi run python scripts/21_bajar_infraestructura_osm.py
```

**2. Wflow (cuenca)**

```bash
pixi run python scripts/11_bajar_capas_wflow_gee.py
pixi run python scripts/13_recortar_rios_lin.py
pixi run python scripts/14_bajar_lluvia_imerg.py
pixi run python scripts/16_bajar_clima_era5land_gee.py
pixi run -e wflow python scripts/12_armar_catalogo_wflow.py
pixi run -e wflow hydromt build wflow_sbm modelos/wflow-piura -i config/wflow_build_piura.yml -d datos/wflow/catalogo_piura.yml
pixi run -e wflow hydromt update wflow_sbm modelos/wflow-piura -o modelos/wflow-piura-era5land -i config/wflow_update_lluvia_era5land.yml -d datos/wflow/catalogo_piura.yml
pixi run -e wflow python scripts/17_correr_wflow_y_comparar.py modelos/wflow-piura modelos/wflow-piura-era5land
```

Escenario de 1998 (opcional, para la sensibilidad): las instrucciones están en la cabecera de `config/wflow_update_1998.yml`. Luego:

```bash
pixi run -e wflow python scripts/24_sensibilidad_wflow.py
pixi run python scripts/29_grafico_caudal_final.py
```

**3. SFINCS (inundación) y examen**

```bash
pixi run python scripts/18_armar_sfincs.py modelos/sfincs-final --qinf 1 --inicio 2017-03-15
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W)/modelos/sfincs-final:/data" deltares/sfincs-cpu:latest > modelos/sfincs-final/sfincs_log.txt 2>&1
pixi run python scripts/19_exportar_mancha_s1.py
pixi run python scripts/20_examen_sfincs_vs_satelite.py modelos/sfincs-final
pixi run python scripts/26_verificar_con_optico.py modelos/sfincs-final
pixi run python scripts/22_impacto.py modelos/sfincs-final
pixi run python scripts/25_animacion_inundacion.py modelos/sfincs-final
```

SFINCS tarda unos 20 minutos con 12 hilos.

## Notas

- **Pasa la carpeta del modelo como argumento.** Varios scripts (20, 22, 26) usan por defecto una corrida previa.
- `08` y `10` bajan ERA5 por Copernicus CDS. Son un respaldo: la receta final usa IMERG y ERA5-Land vía Earth Engine.
- `15` y `23` hacen gráficos y las imágenes del comparador web. `03` reproduce el ejemplo oficial de SFINCS para probar la instalación. `28` es un caso aparte (Arequipa).
- La numeración tiene un hueco (27): ese script era material de divulgación y no se publica.
- Los datos globales se actualizan (Open Buildings, OSM). Al reproducir hoy, la exposición puede variar un poco.
