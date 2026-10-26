"""Baja de OpenStreetMap (API pública de Overpass) la infraestructura crítica del dominio de inundación.

- Educación: amenity = school, kindergarten, college, university
- Salud: amenity = hospital, clinic, doctors; healthcare = centre, hospital, clinic
- Vías principales: highway = motorway, trunk, primary, secondary (para ver qué rutas quedarían cortadas)

Polígonos (p. ej. el terreno de un colegio) se reducen a su punto central.
Lee: nada. Escribe: geo/osm-educacion.geojson, geo/osm-salud.geojson, geo/osm-vias.geojson (sí van a git: son livianos)
"""
import json
import time
from pathlib import Path

import requests

RECUADRO = (-6.0, -81.0, -5.05, -80.4)  # sur, oeste, norte, este
SERVIDORES = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
              "https://overpass.private.coffee/api/interpreter"]  # espejos públicos, por si uno está saturado
CONSULTAS = {
    "educacion": '(nwr["amenity"~"^(school|kindergarten|college|university)$"]({b}););',
    "salud": '(nwr["amenity"~"^(hospital|clinic|doctors)$"]({b});nwr["healthcare"~"^(centre|hospital|clinic)$"]({b}););',
    "vias": '(way["highway"~"^(motorway|trunk|primary|secondary)$"]({b}););',
}
caja = ",".join(map(str, RECUADRO))

for nombre, filtro in CONSULTAS.items():
    salida = "out geom;" if nombre == "vias" else "out center tags;"
    consulta = f"[out:json][timeout:120];{filtro.format(b=caja)}{salida}"
    for url in SERVIDORES * 2:
        try:
            respuesta = requests.post(url, data={"data": consulta}, timeout=180,
                                      headers={"User-Agent": "enso-floods-peru (demo sin fines de lucro)"})
            respuesta.raise_for_status()
            elementos = respuesta.json()["elements"]
            break
        except (requests.RequestException, ValueError) as error:
            print(f"  {nombre}: {url.split('/')[2]} falló ({type(error).__name__}), reintentando…")
            time.sleep(10)
    else:
        raise SystemExit(f"No se pudo bajar {nombre} de ningún servidor de Overpass")

    features = []
    for e in elementos:
        etiquetas = e.get("tags", {})
        propiedades = {"osm_id": f"{e['type']}/{e['id']}", "nombre": etiquetas.get("name", "(sin nombre)"),
                       "tipo": etiquetas.get("amenity") or etiquetas.get("healthcare") or etiquetas.get("highway")}
        if nombre == "vias":
            coords = [[p["lon"], p["lat"]] for p in e.get("geometry", [])]
            if len(coords) < 2:
                continue
            geometria = {"type": "LineString", "coordinates": coords}
        else:
            punto = e.get("center") or {"lat": e.get("lat"), "lon": e.get("lon")}
            if punto["lat"] is None:
                continue
            geometria = {"type": "Point", "coordinates": [punto["lon"], punto["lat"]]}
        features.append({"type": "Feature", "properties": propiedades, "geometry": geometria})

    archivo = Path(f"geo/osm-{nombre}.geojson")
    archivo.write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False), encoding="utf-8")
    tipos = {}
    for f in features:
        tipos[f["properties"]["tipo"]] = tipos.get(f["properties"]["tipo"], 0) + 1
    print(f"{nombre:10} {len(features):>5} elementos → {archivo}  {dict(sorted(tipos.items(), key=lambda kv: -kv[1]))}")
    time.sleep(5)  # cortesía con el servidor público
