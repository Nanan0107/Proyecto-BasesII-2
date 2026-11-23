"""Indexa el dataset final (JSONL o CSV) en el core de insectos.

El archivo debe tener los nombres de campo definidos en solr/crear_esquema.py.
Sirve tanto para la muestra (datos/generar_muestra.py) como para el archivo
que produzca el notebook de Spark.

Uso:
    python solr/indexar.py datos/muestra/insectos_muestra.jsonl --borrar
    python solr/indexar.py salida_spark.csv --lote 10000

--borrar elimina todos los documentos antes de cargar (recarga limpia).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Iterator

import httpx

SOLR_URL = os.environ.get("SOLR_URL", "http://localhost:8983/solr/insectos")

NUMERICOS = {"anio": int, "mes": int, "latitud": float, "longitud": float,
             "elevacion_m": float, "area_protegida_km2": float}


def leer_jsonl(ruta: Path) -> Iterator[dict]:
    with ruta.open(encoding="utf-8") as fh:
        for linea in fh:
            if linea.strip():
                yield json.loads(linea)


def leer_csv(ruta: Path) -> Iterator[dict]:
    with ruta.open(encoding="utf-8", newline="") as fh:
        for fila in csv.DictReader(fh):
            doc = {}
            for k, v in fila.items():
                if v in ("", None):
                    continue  # en Solr, un campo ausente = valor faltante
                if k in NUMERICOS:
                    v = NUMERICOS[k](v)
                elif k == "dentro_asp":
                    v = v.strip().lower() in ("true", "1", "si", "sí")
                doc[k] = v
            if "ubicacion" not in doc and "latitud" in doc and "longitud" in doc:
                doc["ubicacion"] = f"{doc['latitud']},{doc['longitud']}"
            yield doc


def lotes(docs: Iterator[dict], tam: int) -> Iterator[list[dict]]:
    lote: list[dict] = []
    for d in docs:
        lote.append(d)
        if len(lote) >= tam:
            yield lote
            lote = []
    if lote:
        yield lote


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("archivo", type=Path)
    p.add_argument("--solr", default=SOLR_URL)
    p.add_argument("--lote", type=int, default=5000)
    p.add_argument("--borrar", action="store_true", help="borrar todo antes de indexar")
    args = p.parse_args()

    if not args.archivo.exists():
        sys.exit(f"No existe {args.archivo}")
    lector = leer_csv if args.archivo.suffix.lower() == ".csv" else leer_jsonl

    inicio = time.time()
    total = 0
    with httpx.Client(base_url=args.solr, timeout=120) as c:
        if args.borrar:
            c.post("/update", json={"delete": {"query": "*:*"}}, params={"commit": "true"}).raise_for_status()
            print("Documentos anteriores borrados.")
        for lote in lotes(lector(args.archivo), args.lote):
            r = c.post("/update", json=lote)
            if r.status_code != 200:
                sys.exit(f"Error al indexar (documento ~{total}): {r.text[:500]}")
            total += len(lote)
            print(f"\r{total} documentos enviados…", end="", flush=True)
        c.post("/update", json={"commit": {}}).raise_for_status()
        n = c.get("/select", params={"q": "*:*", "rows": 0}).json()["response"]["numFound"]

    print(f"\nListo: {total} enviados, {n} en el índice ({time.time() - inicio:.1f} s).")


if __name__ == "__main__":
    main()
