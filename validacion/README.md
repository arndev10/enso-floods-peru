# validacion/: qué es cada archivo

Los resultados que valen son los de la **corrida final** (`sfincs-final`). Las corridas previas se dejan para que se vea cómo se llegó a ella.

## Corrida final (usar estos)

| Archivo | Qué es | Script |
|---|---|---|
| `examen-sfincs-final.png/json` | Modelo contra radar Sentinel-1 del 1-abr-2017: aciertos, omisiones, falsas alarmas y CSI | 20 |
| `verificacion-optico-sfincs-final.json` | Segunda opinión con Landsat 8 (4-abr-2017) y examen contra radar + Landsat (CSI 0.505) | 26 |
| `impacto-sfincs-final.json/csv` | Exposición en el máximo del evento: edificios, personas, colegios, salud y vías, por profundidad | 22 |
| `animacion-sfincs-final.mp4`, `animacion-sfincs-final-vertical.mp4` | Animación de la inundación simulada (horizontal y vertical) | 25 |
| `caudal-sanchez-cerro-2017.png` | Caudal simulado (Wflow IMERG, Wflow ERA5-Land ajustado, GloFAS) contra el pico oficial | 29 |
| `sensibilidad-wflow.csv` | Sensibilidad de Wflow en 2017 y 1998 (pico, fecha y error por variante) | 24 |

## Datos de referencia

| Archivo | Qué es | Script |
|---|---|---|
| `s1-mancha-2017-04-01.png/json` | Mancha de agua del radar Sentinel-1 (369.5 km² en el dominio) | 05 |
| `s1_observado_30m.tif`, `s1_evaluable_30m.tif` | La misma mancha a 30 m y la zona donde el radar sí puede juzgar (no se versionan; se regeneran) | 19 |
| `landsat_agua_2017-04-04_30m.tif` | Agua en Landsat 8 a 30 m (no se versiona; se regenera) | 26 |
| `optico-l8-2017-04-04.png`, `optico-s2-2017-03-31.png` | Imágenes ópticas de esos días (Sentinel-2 casi todo nube) | 26 |
| `lluvia-cuenca-2017.png/csv` | Lluvia diaria media sobre la cuenca, IMERG (y ERA5 si está) | 15 |
| `fase0-ejemplo-sfincs.png` | Prueba de instalación: el ejemplo oficial de SFINCS sale idéntico a la referencia de Deltares | 03 |
| `arequipa-caminos-agua.png` | Caso aparte: caminos naturales del agua en Arequipa (feb-2026) | 28 |

## Corridas previas (historial)

| Archivo | Corrida | Por qué no es la final |
|---|---|---|
| `examen-sfincs-bajo-piura.*`, `verificacion-optico-sfincs-bajo-piura.json` | 1: sin infiltración, desde 1-mar | Encharca la lluvia sobre la arena: cientos de falsas alarmas (CSI radar 0.27) |
| `examen-sfincs-bajo-piura-inf.*`, `verificacion-optico-sfincs-bajo-piura-inf.json` | 2: infiltración 2 mm/h, desde 15-mar | Pierde aciertos (CSI radar + Landsat 0.47) |
| `examen-sfincs-bajo-piura-inf1.*`, `verificacion-optico-sfincs-bajo-piura-inf1.json` | 3: infiltración 1 mm/h, pico sin anclar a la hora | La final es igual pero con el pico anclado al 27-mar 12:00 hora de Perú |

El impacto de la corrida 1 no se publica: salía inflado por las falsas alarmas.
