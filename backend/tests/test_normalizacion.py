"""Pruebas unitarias de app/solr.py (no necesitan Solr)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.solr import normalizar, preparar_params  # noqa: E402


def test_preparar_params_listas_y_json():
    pares = preparar_params({"q": "*:*", "fq": ["a:1", "b:2"], "json.facet": {"x": {"type": "terms"}},
                             "facet": True, "nada": None})
    assert ("fq", "a:1") in pares and ("fq", "b:2") in pares
    assert ("json.facet", '{"x": {"type": "terms"}}') in pares
    assert ("facet", "true") in pares
    assert all(k != "nada" for k, _ in pares)


def test_normalizar_facets_clasicos():
    datos = {"response": {"numFound": 3, "docs": []},
             "facet_counts": {"facet_fields": {"orden": ["A", 2, "B", 1]},
                              "facet_queries": {"elevacion_m:[0 TO 500}": 2},
                              "facet_ranges": {"anio": {"counts": ["1990", 3], "gap": 5}},
                              "facet_pivot": {"a,b": [{"field": "a", "value": "x", "count": 3,
                                                       "pivot": [{"field": "b", "value": "y", "count": 2}]}]}}}
    f = {x["tipo"]: x for x in normalizar(datos, {})["facets"]}
    assert f["campo"]["buckets"][0] == {"valor": "A", "conteo": 2, "metricas": {}, "hijos": []}
    assert f["consulta"]["buckets"][0]["conteo"] == 2
    assert f["rango"]["metricas"]["gap"] == 5
    assert f["pivot"]["buckets"][0]["hijos"][0]["valor"] == "y"


def test_normalizar_json_facet():
    datos = {"response": {"numFound": 5, "docs": []},
             "facets": {"count": 5, "prom": 10.5,
                        "por_area": {"buckets": [{"val": "X", "count": 5, "avg_e": 1.0,
                                                  "sub": {"buckets": [{"val": "Y", "count": 2}]}}]},
                        "altas": {"count": 1}}}
    f = {x["nombre"]: x for x in normalizar(datos, {})["facets"]}
    b = f["por_area"]["buckets"][0]
    assert b["metricas"] == {"avg_e": 1.0} and b["hijos"][0]["valor"] == "Y"
    assert f["consultas"]["buckets"][0] == {"valor": "altas", "conteo": 1, "metricas": {}, "hijos": [],
                                            "hijos_nombre": None}
    assert f["metricas"]["metricas"]["prom"] == 10.5
