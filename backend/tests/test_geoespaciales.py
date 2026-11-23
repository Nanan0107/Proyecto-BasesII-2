"""Pruebas de las consultas geoespaciales contra el Solr real.

Verifican, con geometría calculada en Python, que lo que devuelve Solr está
realmente dentro del radio / del polígono, y que el filtro espacial viaja en la
consulta a Solr (no se filtra en la aplicación).
"""

import math

from conftest import responder

# Polígono irregular (5 vértices) sobre la península de Osa, en [lat, lon]
OSA = [[8.75, -83.75], [8.70, -83.30], [8.45, -83.25], [8.35, -83.55], [8.50, -83.80]]
SAN_JOSE = (9.93, -84.08)


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def dentro(lat, lon, poligono):
    """Ray casting en el plano lat/lon (suficiente para polígonos pequeños)."""
    adentro = False
    n = len(poligono)
    for i in range(n):
        (y1, x1), (y2, x2) = poligono[i], poligono[(i + 1) % n]
        if (y1 > lat) != (y2 > lat):
            x = x1 + (lat - y1) * (x2 - x1) / (y2 - y1)
            if lon < x:
                adentro = not adentro
    return adentro


def params_texto(r):
    return str(r["solr_params"])


def test_consulta_11_proximidad(cliente):
    r = responder(cliente.post("/api/geo/proximidad",
                               json={"lat": SAN_JOSE[0], "lon": SAN_JOSE[1], "radio_km": 15, "filas": 500}))
    assert r["numFound"] > 0
    distancias = [haversine_km(*SAN_JOSE, d["latitud"], d["longitud"]) for d in r["docs"]]
    assert max(distancias) <= 15.2, "Hay registros fuera del radio"
    assert distancias == sorted(distancias) or all(abs(a - b) < 0.05 for a, b in
                                                    zip(distancias, sorted(distancias))), \
        "Los resultados deben ir del más cercano al más lejano"


def test_consulta_11_con_filtro(cliente):
    base = {"lat": 8.54, "lon": -83.58, "radio_km": 20, "filas": 200}
    todos = responder(cliente.post("/api/geo/proximidad", json=base))
    lepi = responder(cliente.post("/api/geo/proximidad", json={**base, "filtros": {"orden": "Lepidoptera"}}))
    assert 0 < lepi["numFound"] < todos["numFound"]
    assert all(d.get("orden", "Lepidoptera") == "Lepidoptera" for d in lepi["docs"])


def test_consulta_12_poligono(cliente, total):
    r = responder(cliente.post("/api/geo/poligono", json={"vertices": OSA, "filas": 2000}))
    assert 0 < r["numFound"] < total
    fuera = [d for d in r["docs"] if not dentro(d["latitud"], d["longitud"], OSA)]
    assert not fuera, f"{len(fuera)} puntos devueltos están fuera del polígono"
    assert "POLYGON" in params_texto(r).upper(), "El polígono debe enviarse a Solr como WKT"


def test_consulta_12_poligono_cerrado_o_no(cliente):
    abierto = responder(cliente.post("/api/geo/poligono", json={"vertices": OSA, "filas": 0}))
    cerrado = responder(cliente.post("/api/geo/poligono", json={"vertices": OSA + [OSA[0]], "filas": 0}))
    assert abierto["numFound"] == cerrado["numFound"], "Repetir el primer vértice no debe cambiar el resultado"


def test_consulta_13_poligono_facets(cliente):
    r = responder(cliente.post("/api/geo/poligono-facets",
                               json={"vertices": OSA, "campo_facet": "orden", "filas": 100}))
    con = [f for f in r["facets"] if f["buckets"]]
    assert con, "Falta el facet"
    suma = sum(b["conteo"] for b in con[0]["buckets"])
    assert suma == r["numFound"], "Con un campo de un solo valor, los buckets deben sumar el total del polígono"
