"""Pruebas de las 10 consultas convencionales contra el Solr real.

Ejecutar desde la raíz del repo:
    backend/.venv/bin/pytest backend/tests -v
    backend/.venv/bin/pytest backend/tests -k consulta_3     # solo una

Una prueba se salta (SKIPPED) mientras su función lance NotImplementedError.
No verifican CÓMO se escribió la consulta, sino que el resultado tenga sentido:
que los documentos cumplan las condiciones y que los facets tengan la forma
esperada.
"""

from conftest import responder


def ejecutar(cliente, n, filas=50, **parametros):
    return responder(cliente.post(f"/api/consultas/{n}", json={"parametros": parametros, "filas": filas}))


def facet_con_buckets(r):
    con = [f for f in r["facets"] if f["buckets"]]
    assert con, f"La respuesta no trae ningún facet con buckets: {r['facets']}"
    return con[0]


# ----------------------------------------------------------------- búsqueda
def test_consulta_1_texto_general(cliente):
    r = ejecutar(cliente, 1, texto="Morpho", campo="texto")
    assert r["numFound"] > 0
    assert all("morpho" in d.get("nombre_cientifico", "").lower() for d in r["docs"])


def test_consulta_1_campo_exacto(cliente):
    r = ejecutar(cliente, 1, texto="Corcovado", campo="area_protegida")
    assert r["numFound"] > 0
    assert all(d["area_protegida"] == "Corcovado" for d in r["docs"])


def test_consulta_1_valor_con_espacios(cliente):
    r = ejecutar(cliente, 1, texto="Volcán Poás", campo="area_protegida")
    assert r["numFound"] > 0, "Los valores con espacios deben ir entre comillas"
    assert all(d["area_protegida"] == "Volcán Poás" for d in r["docs"])


def test_consulta_2_logicos(cliente):
    cats = ["Parque Nacional", "Reserva Biológica"]
    r = ejecutar(cliente, 2, orden="Lepidoptera", categorias=cats, excluir_provincia="Limón")
    assert r["numFound"] > 0
    for d in r["docs"]:
        assert d["orden"] == "Lepidoptera"
        assert d["categoria_manejo"] in cats
        assert d["provincia"] != "Limón"


def test_consulta_3_rangos(cliente):
    r = ejecutar(cliente, 3, elev_min=1000, elev_max=2500, fecha_desde="1995-01-01", fecha_hasta="2005-12-31")
    assert r["numFound"] > 0
    for d in r["docs"]:
        assert 1000 <= d["elevacion_m"] <= 2500
        assert "1995-01-01" <= d["fecha_evento"][:10] <= "2005-12-31"


def test_consulta_4_filtros_y_orden(cliente):
    r = ejecutar(cliente, 4, orden="Coleoptera", area_conservacion="ACOSA", etapa_vida="", estacion="",
                 orden_1="fecha_evento desc", orden_2="elevacion_m asc")
    assert r["numFound"] > 0
    docs = r["docs"]
    for d in docs:
        assert d["orden"] == "Coleoptera" and d["area_conservacion"] == "ACOSA"
    claves = [(d["fecha_evento"], -d["elevacion_m"]) for d in docs]
    assert claves == sorted(claves, reverse=True), "No respeta fecha desc y luego elevación asc"


def test_consulta_4_filtros_vacios_no_filtran(cliente, total):
    r = ejecutar(cliente, 4, orden="", area_conservacion="", etapa_vida="", estacion="",
                 orden_1="elevacion_m desc", orden_2="")
    assert r["numFound"] == total, "Un filtro vacío no debe restringir los resultados"


# ------------------------------------------------------------------- facets
def test_consulta_5_field_facet(cliente, total):
    r = ejecutar(cliente, 5, campo="orden", limite=5, minimo=1)
    f = facet_con_buckets(r)
    conteos = [b["conteo"] for b in f["buckets"]]
    assert len(conteos) <= 5
    assert conteos == sorted(conteos, reverse=True)
    assert sum(conteos) <= total


def test_consulta_6_range_facet(cliente):
    r = ejecutar(cliente, 6, campo="elevacion_m", inicio=0, fin=3500, intervalo=500)
    f = facet_con_buckets(r)
    valores = [float(b["valor"]) for b in f["buckets"]]
    assert valores[:3] == [0.0, 500.0, 1000.0]
    assert len(valores) == 7


def test_consulta_6_por_anio(cliente):
    r = ejecutar(cliente, 6, campo="anio", inicio=1985, fin=2016, intervalo=5)
    f = facet_con_buckets(r)
    assert [int(float(b["valor"])) for b in f["buckets"]][:2] == [1985, 1990]


def test_consulta_7_query_facets(cliente):
    r = ejecutar(cliente, 7, orden="")
    f = facet_con_buckets(r)
    assert len(f["buckets"]) >= 3, "Se esperan al menos 3 condiciones"
    assert all(b["conteo"] >= 0 for b in f["buckets"])


def test_consulta_8_anidado(cliente):
    r = ejecutar(cliente, 8, campo_padre="area_conservacion", campo_hijo="orden", limite_padre=5, limite_hijo=3)
    f = facet_con_buckets(r)
    assert len(f["buckets"]) <= 5
    for b in f["buckets"]:
        assert b["hijos"], f"El bucket {b['valor']} no tiene segundo nivel"
        assert len(b["hijos"]) <= 3
        assert sum(h["conteo"] for h in b["hijos"]) <= b["conteo"]


def test_consulta_9_estadisticas(cliente):
    r = ejecutar(cliente, 9, campo_grupo="area_protegida", limite=10)
    f = facet_con_buckets(r)
    for b in f["buckets"]:
        nums = sorted(v for v in b["metricas"].values() if isinstance(v, (int, float)))
        assert len(b["metricas"]) >= 3, f"Se esperan promedio, mínimo y máximo en {b['valor']}"
        assert nums, b


def test_consulta_10_ranking(cliente):
    r = ejecutar(cliente, 10, area_protegida="Corcovado", limite=5)
    f = facet_con_buckets(r)
    assert len(f["buckets"]) <= 5
    nombres = [b["valor"] for b in f["buckets"]]
    assert all(" " in n for n in nombres), "El ranking debe ser de especies (género + epíteto)"
    # Todos los conteos deben pertenecer a Corcovado
    solo_area = ejecutar(cliente, 1, filas=0, texto="Corcovado", campo="area_protegida")
    assert sum(b["conteo"] for b in f["buckets"]) <= solo_area["numFound"]
