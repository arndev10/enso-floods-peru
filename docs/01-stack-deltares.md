# 01 — Stack de Deltares (Holanda)

Deltares es el instituto holandés independiente de investigación en agua, suelo y deltas. Publica la mayoría de sus herramientas como open source. Todas se encadenan: **HydroMT arma, Wflow y SFINCS simulan, Delft-FIAT calcula el impacto.**

| Herramienta | Qué hace | Rol en este proyecto | Licencia |
|---|---|---|---|
| **HydroMT** (Python) | Arma modelos automáticamente a partir de datos globales, con un catálogo de fuentes ya configuradas | Columna vertebral: evita recopilar datos a mano | Open source (MIT) |
| **hydromt_wflow** | Plugin para construir modelos Wflow | Fase 2 | Open source |
| **Wflow** (Julia; existe versión Python) | Modelo hidrológico distribuido: lluvia → escorrentía → caudal | Fase 2: caudal del río Piura | Open source |
| **hydromt_sfincs** | Plugin para construir modelos SFINCS | Fase 3 | Open source |
| **SFINCS** | Modelo de inundación rápido (fluvial, pluvial y costero) | Fase 3: mancha y profundidad de agua | Open source |
| **Delft-FIAT** + **hydromt_fiat** | Impacto: daño por vivienda y personas afectadas, con curvas profundidad-daño | Fase 4 | Open source |
| **Delft3D FM / D-HYDRO Suite** | Hidráulica de detalle (1D/2D/3D) | No para la demo; para diseño de ingeniería más adelante | Open source (núcleo) |
| **Delft-FEWS** | Plataforma de alerta temprana operativa (une pronósticos + modelos en tiempo real) | Visión a futuro si esto escala a algo operativo | Licencia gratuita, no open source |
| **RA2CE** | Criticidad de redes viales ante inundaciones | Opcional en Fase 4 (vías que quedan cortadas) | Open source |

## Alternativas internacionales (para comparar o complementar)

| Herramienta | Origen | Nota |
|---|---|---|
| **CLIMADA** | ETH Zúrich | Plataforma Python de riesgo e impacto; alternativa a Delft-FIAT |
| **LISFLOOD-FP** | Universidad de Bristol | Modelo de inundación 2D, alternativa a SFINCS |
| **HEC-HMS / HEC-RAS** | Cuerpo de Ingenieros de EE.UU. | Estándar en ingeniería peruana; útil para que un hidráulico local entienda o contraste |
| **Iber** | España | Modelo 2D gratuito, muy usado en Latinoamérica |
| **GloFAS** | Copernicus (UE) | Pronóstico global de caudales; referencia para la visión de alerta temprana |
| **Google Flood Hub** | Google | Pronóstico de inundaciones con IA; verificar cobertura en Perú |

## Documentación oficial
- HydroMT: https://deltares.github.io/hydromt/
- SFINCS: https://sfincs.readthedocs.io/
- Wflow: https://deltares.github.io/Wflow.jl/
- Delft-FIAT: https://deltares.github.io/Delft-FIAT/
- Código: https://github.com/Deltares

(Links por verificar en la Fase 0; si alguno cambió, actualizar aquí.)
