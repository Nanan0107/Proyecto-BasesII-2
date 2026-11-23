"""Cliente de Apache Solr: envía parámetros a /select y normaliza la respuesta.

Las funciones de app/consultas/ construyen los parámetros; este módulo es el
único que habla HTTP con Solr. Así la interfaz puede mostrar exactamente qué
se le envió a Solr y la respuesta llega siempre con la misma forma.
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlencode

import httpx

SOLR_URL = os.environ.get("SOLR_URL", "http://localhost:8983/solr/insectos")

_cliente = httpx.Client(base_url=SOLR_URL, timeout=30)


class SolrError(Exception):
    """Error devuelto por Solr (sintaxis, campo inexistente, etc.)."""

    def __init__(self, mensaje: str, params: dict | None = None, status: int = 400):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.params = params or {}
        self.status = status


def preparar_params(params: dict[str, Any]) -> list[tuple[str, str]]:
    """Convierte el dict de parámetros a la lista (clave, valor) que Solr espera.

    - Las listas se envían como parámetros repetidos (fq=…&fq=…).
    - Los dicts (p. ej. json.facet) se serializan a JSON.
    - None se omite; los booleanos se envían como true/false.
    """
    salida: list[tuple[str, str]] = []
    for clave, valor in params.items():
        valores = valor if isinstance(valor, (list, tuple)) else [valor]
        for v in valores:
            if v is None:
                continue
            if isinstance(v, bool):
                v = "true" if v else "false"
            elif isinstance(v, (dict, list)):
                v = json.dumps(v, ensure_ascii=False)
            salida.append((clave, str(v)))
    return salida


def url_equivalente(params: dict[str, Any]) -> str:
    """URL GET equivalente (para copiarla al navegador o al Admin UI)."""
    return f"{SOLR_URL}/select?{urlencode(preparar_params(params))}"


def ejecutar(params: dict[str, Any]) -> dict[str, Any]:
    """Ejecuta la consulta en Solr y devuelve la respuesta normalizada."""
    pares = preparar_params({"wt": "json", **params})
    try:
        # POST con formulario: los polígonos WKT pueden ser largos para una URL.
        r = _cliente.post("/select", content=urlencode(pares),
                          headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})
    except httpx.HTTPError as e:
        raise SolrError(f"No se pudo conectar con Solr en {SOLR_URL}: {e}", params, 503) from e

    try:
        datos = r.json()
    except ValueError:
        raise SolrError(f"Solr respondió algo que no es JSON (HTTP {r.status_code})", params, 502)

    if r.status_code != 200 or "error" in datos:
        msg = datos.get("error", {}).get("msg", r.text[:300])
        raise SolrError(f"Solr rechazó la consulta: {msg}", params, 400)

    return normalizar(datos, params)


def ping() -> dict[str, Any]:
    try:
        r = _cliente.get("/select", params={"q": "*:*", "rows": 0})
        r.raise_for_status()
        return {"ok": True, "url": SOLR_URL, "documentos": r.json()["response"]["numFound"]}
    except (httpx.HTTPError, KeyError, ValueError) as e:
        return {"ok": False, "url": SOLR_URL, "error": str(e)}


# ---------------------------------------------------------------------------
# Normalización de facets
#
# Solr devuelve los facets en formatos distintos según la API usada:
#   - Facets clásicos: response["facet_counts"] con facet_fields, facet_ranges,
#     facet_queries y facet_pivot.
#   - JSON Facet API: response["facets"] (árbol con buckets y métricas).
#   - Componente de estadísticas: response["stats"]["stats_fields"].
# La interfaz recibe siempre una lista de facets con esta forma:
#   {"nombre", "tipo", "buckets": [{"valor", "conteo", "metricas", "hijos"}],
#    "metricas": {...}}
# ---------------------------------------------------------------------------

def normalizar(datos: dict, params: dict) -> dict[str, Any]:
    resp = datos.get("response", {})
    facets: list[dict] = []

    fc = datos.get("facet_counts", {})
    for campo, plano in fc.get("facet_fields", {}).items():
        facets.append({"nombre": campo, "tipo": "campo", "buckets": _pares(plano), "metricas": {}})

    for campo, info in fc.get("facet_ranges", {}).items():
        buckets = _pares(info.get("counts", []))
        metricas = {k: info[k] for k in ("gap", "start", "end", "before", "after", "between") if k in info}
        facets.append({"nombre": campo, "tipo": "rango", "buckets": buckets, "metricas": metricas})

    if fc.get("facet_queries"):
        buckets = [{"valor": q, "conteo": n, "metricas": {}, "hijos": []} for q, n in fc["facet_queries"].items()]
        facets.append({"nombre": "facet.query", "tipo": "consulta", "buckets": buckets, "metricas": {}})

    for clave, lista in fc.get("facet_pivot", {}).items():
        facets.append({"nombre": clave, "tipo": "pivot", "buckets": [_pivot(b) for b in lista], "metricas": {}})

    if "facets" in datos:
        facets.extend(_json_facets(datos["facets"]))

    stats = {}
    for campo, s in (datos.get("stats", {}).get("stats_fields") or {}).items():
        if s:
            stats[campo] = {k: v for k, v in s.items() if isinstance(v, (int, float)) or k == "facets"}

    return {
        "numFound": resp.get("numFound", 0),
        "start": resp.get("start", 0),
        "docs": resp.get("docs", []),
        "facets": facets,
        "stats": stats,
        "qtime": datos.get("responseHeader", {}).get("QTime"),
        "solr_params": params,
        "solr_url": url_equivalente(params),
    }


def _pares(plano: list) -> list[dict]:
    """facet_fields viene como lista plana [valor1, n1, valor2, n2, …]."""
    return [{"valor": plano[i], "conteo": plano[i + 1], "metricas": {}, "hijos": []}
            for i in range(0, len(plano) - 1, 2)]


def _pivot(b: dict) -> dict:
    metricas = {}
    for campo, s in (b.get("stats", {}).get("stats_fields") or {}).items():
        for k, v in (s or {}).items():
            if isinstance(v, (int, float)):
                metricas[f"{k}({campo})"] = v
    return {"valor": b.get("value"), "conteo": b.get("count", 0), "metricas": metricas,
            "hijos": [_pivot(h) for h in b.get("pivot", [])], "campo": b.get("field")}


def _es_numero(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _json_bucket(b: dict) -> dict:
    metricas, hijos, hijos_nombre = {}, [], None
    for k, v in b.items():
        if k in ("val", "count"):
            continue
        if _es_numero(v):
            metricas[k] = v
        elif isinstance(v, dict) and "buckets" in v and not hijos:
            hijos = [_json_bucket(h) for h in v["buckets"]]
            hijos_nombre = k
        elif isinstance(v, dict) and "count" in v:
            # sub-facet de tipo query dentro del bucket
            metricas[k] = v["count"]
    return {"valor": b.get("val"), "conteo": b.get("count", 0), "metricas": metricas,
            "hijos": hijos, "hijos_nombre": hijos_nombre}


def _json_facets(raiz: dict) -> list[dict]:
    salida: list[dict] = []
    globales: dict[str, Any] = {}
    consultas: list[dict] = []
    for nombre, v in raiz.items():
        if nombre == "count":
            continue
        if _es_numero(v):
            globales[nombre] = v
        elif isinstance(v, dict) and "buckets" in v:
            tipo = "rango" if v["buckets"] and _es_numero(v["buckets"][0].get("val")) else "json"
            extra = {k: v[k]["count"] for k in ("before", "after", "between") if isinstance(v.get(k), dict)}
            salida.append({"nombre": nombre, "tipo": tipo, "buckets": [_json_bucket(b) for b in v["buckets"]],
                           "metricas": extra})
        elif isinstance(v, dict) and "count" in v:
            b = _json_bucket(v)
            b["valor"] = nombre
            consultas.append(b)
    if consultas:
        salida.append({"nombre": "consultas", "tipo": "consulta", "buckets": consultas, "metricas": {}})
    if globales:
        salida.append({"nombre": "metricas", "tipo": "metricas", "buckets": [],
                       "metricas": {"count": raiz.get("count"), **globales}})
    return salida
