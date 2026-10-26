# SFINCS con Docker

- Imagen oficial: `deltares/sfincs-cpu:latest` (~220 MB). Workdir `/data`, comando `sfincs`.
- El release v2.4.0 de GitHub no trae binarios; el `.exe` de Windows está en el portal de descargas de Deltares (pide registro). Docker evita eso.
- Docker Desktop tiene que estar abierto (si no: "failed to connect to the docker API ... dockerDesktopLinuxEngine").

## Correr un modelo
Desde Git Bash, con la carpeta del modelo (la que tiene `sfincs.inp`):

```bash
MSYS_NO_PATHCONV=1 docker run --rm -v "D:/ruta/al/modelo:/data" deltares/sfincs-cpu:latest > sfincs_log.txt 2>&1
```

`MSYS_NO_PATHCONV=1` evita que Git Bash convierta `/data` en una ruta de Windows.

## Prueba de la Fase 0 (23-oct-2026)
Ejemplo `sfincs_compound` de hydromt_sfincs (251×108 celdas de 50 m, 2 días): corrió en 9 s y salió **idéntico** a la referencia de Deltares (7,034 celdas mojadas, diferencia 0.0000 m, CSI 1.000). Script: `scripts/03_comparar_ejemplo_sfincs.py`; figura en `validacion/fase0-ejemplo-sfincs.png`.
