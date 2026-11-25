"""Consultas geoespaciales — LAS ESCRIBE FABIÁN.

Mismo contrato que convencionales.py: reciben datos de la interfaz y devuelven
un dict de parámetros Solr. El campo espacial se llama `ubicacion` y es de tipo
SpatialRecursivePrefixTreeFieldType con JTS (acepta polígonos WKT).

Importante (requisito del enunciado): el filtro espacial lo hace Solr. Estas
funciones NO pueden pedir todos los registros y filtrarlos en Python.

Cada función recibe además `filtros`: dict con condiciones sobre otros
atributos elegidas en el mapa (hoy: {"orden": "Lepidoptera"} o {}), para cumplir
«consultas que combinen filtros geoespaciales con condiciones sobre otros
atributos». Y `filas`: cuántos puntos dibujar en el mapa.

Los documentos devueltos deben incluir al menos id, latitud y longitud (la API
los agrega a "fl" si faltan).

Guía paso a paso: docs/guia-solr.md (Paso 4).
"""

from __future__ import annotations

def igual(campo: str, valor) -> str:
    """Condición de coincidencia exacta sobre un campo string: campo:"valor"."""
    return f"{campo}:{comillas(str(valor).strip())}"

def proximidad(lat: float, lon: float, radio_km: float, filtros: dict, filas: int) -> dict:
    """11. Registros a menos de `radio_km` del punto (lat, lon), los más cercanos
    primero, e idealmente con la distancia de cada uno en un campo "dist".
    """
    orden = (filtros.get("orden") or "").strip()
    fq = [igual(campo, valor) for campo, valor in filtros.items()]

    return {
        "q":"*:*",
        "fq":fq,
    } 
    raise NotImplementedError


def poligono(vertices: list[list[float]], filtros: dict, filas: int) -> dict:
    """12. Registros dentro del polígono dibujado.

    `vertices`: [[lat, lon], [lat, lon], ...] en el orden en que se hicieron
    clic (mínimo 3, sin repetir el primero al final). Ojo: WKT usa «lon lat».
    """
    raise NotImplementedError


def poligono_facets(vertices: list[list[float]], campo_facet: str, filtros: dict, filas: int) -> dict:
    """13. Mismo filtro que `poligono` + un facet sobre `campo_facet`
    (p. ej. "orden") con los registros que quedaron dentro.
    """
    raise NotImplementedError
