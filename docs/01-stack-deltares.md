# 01 · Stack de Deltares (Países Bajos)

Deltares es el instituto holandés independiente de investigación en agua, suelo y deltas. Publica la mayoría de sus herramientas como software abierto, y están pensadas para encadenarse: **HydroMT arma los modelos, Wflow y SFINCS simulan, Delft-FIAT calcula el daño.**

| Herramienta | Qué hace | En este proyecto |
|---|---|---|
| **HydroMT** (Python) | Arma modelos a partir de datos globales mediante catálogos de fuentes | ✅ Usado, con un catálogo propio (`scripts/12`) porque el de Deltares apunta a su disco interno |
| **hydromt_wflow** 1.1 | Construye modelos Wflow | ✅ Recetas en `config/` |
| **Wflow** 1.0.4 (Julia) | Modelo hidrológico distribuido: lluvia → escorrentía → caudal | ✅ Caudal del río Piura en Sánchez Cerro |
| **hydromt_sfincs** 1.2 | Construye modelos SFINCS | ✅ `scripts/18` |
| **SFINCS** (Docker `deltares/sfincs-cpu`) | Inundación rápida 2D (fluvial, pluvial y costera) con subgrid | ✅ Mancha y profundidad en el Bajo Piura |
| **Delft-FIAT** + hydromt_fiat | Daño por vivienda con curvas profundidad-daño | ❌ No usado todavía. La exposición se calcula con un script propio (`scripts/22`) y no estima daño económico |
| **Delft3D FM / D-HYDRO** | Hidráulica de detalle 1D/2D/3D | ❌ Fuera de alcance: es para diseño de ingeniería |
| **Delft-FEWS** | Plataforma de alerta temprana operativa | ❌ Solo como referencia de hacia dónde podría crecer algo así |

## Alternativas para comparar

| Herramienta | Origen | Nota |
|---|---|---|
| **HEC-HMS / HEC-RAS** | Cuerpo de Ingenieros de EE.UU. | Estándar en la ingeniería peruana. Útil para contrastar con estudios locales |
| **Iber** | España | Modelo 2D gratuito, muy usado en Latinoamérica |
| **LISFLOOD-FP** | Universidad de Bristol | Alternativa a SFINCS |
| **CLIMADA** | ETH Zúrich | Riesgo e impacto en Python. Alternativa a Delft-FIAT |
| **GloFAS** | Copernicus (UE) | Caudal global. Aquí se usó como referencia y subestima el Niño Costero a la mitad |
| **Google Flood Hub** | Google | Pronóstico de inundaciones con IA |

## Documentación oficial

- HydroMT: https://deltares.github.io/hydromt/
- Wflow: https://deltares.github.io/Wflow.jl/
- SFINCS: https://sfincs.readthedocs.io/
- Delft-FIAT: https://deltares.github.io/Delft-FIAT/
- Código: https://github.com/Deltares
