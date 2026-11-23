"""Crea (o actualiza) el esquema del core de insectos mediante la Schema API de Solr.

Requisito: Solr corriendo y el core ya creado (ver docs/guia-solr.md, paso 1).

Uso:
    python solr/crear_esquema.py                       # core "insectos" en localhost:8983
    python solr/crear_esquema.py --solr http://localhost:8983/solr/insectos

Es idempotente: si un campo ya existe lo reemplaza, si no lo crea.
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx

SOLR_URL = os.environ.get("SOLR_URL", "http://localhost:8983/solr/insectos")

# Tipo espacial que acepta polígonos arbitrarios (requisito del enunciado).
# - SpatialRecursivePrefixTreeFieldType (RPT) indexa la geometría en una
#   cuadrícula jerárquica (geohash/quad) y permite Intersects, IsWithin, etc.
# - spatialContextFactory=JTS habilita polígonos WKT (sin JTS solo hay
#   puntos, círculos y rectángulos).
# - distErrPct=0 + maxDistErr=0.001 (1 m): sin aproximación en los bordes del
#   polígono; con el valor por defecto (2,5 %) entran puntos cercanos al borde.
# - geo=true: coordenadas geográficas en grados; distanceUnits=kilometers
#   hace que geofilt/geodist trabajen en km.
TIPO_ESPACIAL = {
    "name": "ubicacion_rpt",
    "class": "solr.SpatialRecursivePrefixTreeFieldType",
    "spatialContextFactory": "JTS",
    "geo": "true",
    "autoIndex": "true",
    "validationRule": "repairBuffer0",
    "distErrPct": "0",
    "maxDistErr": "0.001",
    "distanceUnits": "kilometers",
}

# (nombre, tipo, opciones extra)
CAMPOS = [
    # Taxonomía
    ("nombre_cientifico", "text_general", {"multiValued": False}),
    ("nombre_cientifico_exacto", "string", {"docValues": True}),
    ("orden", "string", {"docValues": True}),
    ("familia", "string", {"docValues": True}),
    ("genero", "string", {"docValues": True}),
    ("especie", "string", {"docValues": True}),
    ("rango_taxonomico", "string", {"docValues": True}),
    # Tiempo
    ("fecha_evento", "pdate", {"docValues": True}),
    ("anio", "pint", {"docValues": True}),
    ("mes", "pint", {"docValues": True}),
    ("estacion", "string", {"docValues": True}),
    # Lugar
    ("provincia", "string", {"docValues": True}),
    ("canton", "string", {"docValues": True}),
    ("localidad", "text_general", {"multiValued": False}),
    ("latitud", "pdouble", {"docValues": True}),
    ("longitud", "pdouble", {"docValues": True}),
    ("ubicacion", "ubicacion_rpt", {}),
    ("elevacion_m", "pdouble", {"docValues": True}),
    ("piso_altitudinal", "string", {"docValues": True}),
    # Área protegida (SINAC)
    ("dentro_asp", "boolean", {"docValues": True}),
    ("area_protegida", "string", {"docValues": True}),
    ("categoria_manejo", "string", {"docValues": True}),
    ("area_conservacion", "string", {"docValues": True}),
    ("area_protegida_km2", "pdouble", {"docValues": True}),
    # Colecta
    ("etapa_vida", "string", {"docValues": True}),
    ("sexo", "string", {"docValues": True}),
    ("protocolo_muestreo", "string", {"docValues": True}),
    ("recolector", "string", {"docValues": True}),
    # Campo de búsqueda general (catch-all)
    ("texto", "text_es", {"multiValued": True, "stored": False}),
]

COPY_FIELDS = [
    ("nombre_cientifico", "nombre_cientifico_exacto"),
    ("nombre_cientifico", "texto"),
    ("orden", "texto"),
    ("familia", "texto"),
    ("localidad", "texto"),
    ("area_protegida", "texto"),
    ("categoria_manejo", "texto"),
]


def schema(cliente: httpx.Client, comando: dict) -> None:
    r = cliente.post("/schema", json=comando)
    datos = r.json()
    if r.status_code != 200 or datos.get("error"):
        sys.exit(f"Error de Solr con {list(comando)}: {datos.get('error', datos)}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--solr", default=SOLR_URL, help="URL del core (default: %(default)s)")
    args = p.parse_args()

    with httpx.Client(base_url=args.solr, timeout=30) as c:
        try:
            actual = c.get("/schema").json()["schema"]
        except (httpx.HTTPError, KeyError):
            sys.exit(f"No se pudo leer el esquema en {args.solr}. ¿Está Solr corriendo y el core creado?")

        # Desactivar el modo «schemaless»: campos desconocidos deben fallar,
        # no crearse con tipos adivinados.
        c.post("/config", json={"set-user-property": {"update.autoCreateFields": "false"}})

        tipos = {t["name"] for t in actual["fieldTypes"]}
        accion = "replace-field-type" if TIPO_ESPACIAL["name"] in tipos else "add-field-type"
        schema(c, {accion: TIPO_ESPACIAL})
        print(f"{accion}: {TIPO_ESPACIAL['name']}")

        # Quitar copyFields previos nuestros para poder reemplazar campos
        existentes_cf = {(cf["source"], cf["dest"]) for cf in actual.get("copyFields", [])}
        for src, dst in COPY_FIELDS:
            if (src, dst) in existentes_cf:
                schema(c, {"delete-copy-field": {"source": src, "dest": dst}})

        existentes = {f["name"] for f in actual["fields"]}
        for nombre, tipo, extra in CAMPOS:
            campo = {"name": nombre, "type": tipo, "indexed": True, "stored": True, **extra}
            accion = "replace-field" if nombre in existentes else "add-field"
            schema(c, {accion: campo})
            print(f"{accion}: {nombre} ({tipo})")

        for src, dst in COPY_FIELDS:
            schema(c, {"add-copy-field": {"source": src, "dest": dst}})
            print(f"add-copy-field: {src} -> {dst}")

    print("Esquema listo.")


if __name__ == "__main__":
    main()
