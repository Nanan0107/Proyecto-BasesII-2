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

# Se reutilizan las utilidades de las consultas convencionales (comillas,
# validación de campos) para que los filtros por atributo se armen igual.
from .convencionales import CATEGORICOS, campo_permitido, igual

CAMPO_ESPACIAL = "ubicacion"
# Campos que necesita el mapa (marcador y ventana emergente).
FL = "id,latitud,longitud,nombre_cientifico,orden,area_protegida,elevacion_m,fecha_evento"


def filtros_atributos(filtros: dict) -> list[str]:
    """Un fq por cada condición sobre otros atributos (p. ej. {"orden": "Lepidoptera"}).

    La API ya elimina las claves vacías; los nombres se validan igual por si
    en el futuro se agregan filtros nuevos.
    """
    return [igual(campo_permitido(campo, CATEGORICOS), valor) for campo, valor in filtros.items()]


def poligono_wkt(vertices: list[list[float]]) -> str:
    """[[lat, lon], ...] (como llegan del mapa) → POLYGON((lon lat, ..., primer punto)).

    WKT usa el orden x y, o sea **longitud latitud**, al revés que el mapa.
    El anillo debe cerrarse repitiendo el primer vértice al final.
    """
    puntos = []
    for v in vertices:
        lat, lon = float(v[0]), float(v[1])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError(f"Vértice fuera de rango: {v}")
        puntos.append((lat, lon))
    # Si el mapa ya lo envió cerrado, no se repite dos veces.
    if len(puntos) > 1 and puntos[0] == puntos[-1]:
        puntos.pop()
    if len(set(puntos)) < 3:
        raise ValueError("El polígono necesita al menos 3 vértices distintos")
    puntos.append(puntos[0])  # cerrar el anillo
    return "POLYGON((" + ", ".join(f"{lon} {lat}" for lat, lon in puntos) + "))"


def filtro_poligono(vertices: list[list[float]]) -> str:
    """fq espacial: documentos cuya ubicación cae dentro del polígono.

    Para puntos, Intersects e IsWithin dan el mismo resultado; Intersects es
    la operación recomendada (más barata) y además incluye los puntos sobre
    el borde. El polígono puede ser irregular (cóncavo, de muchos vértices)
    porque el campo usa JTS; si el usuario lo dibuja cruzado, el esquema lo
    repara (validationRule=repairBuffer0).
    """
    return f'{CAMPO_ESPACIAL}:"Intersects({poligono_wkt(vertices)})"'


def proximidad(lat: float, lon: float, radio_km: float, filtros: dict, filas: int) -> dict:
    """11. Registros a menos de `radio_km` del punto (lat, lon), los más cercanos
    primero, e idealmente con la distancia de cada uno en un campo "dist".
    """
    return {
        "q": "*:*",
        # sfield, pt y d son parámetros compartidos: los usan a la vez el
        # filtro {!geofilt}, el orden geodist() y el campo calculado "dist".
        "sfield": CAMPO_ESPACIAL,
        "pt": f"{float(lat)},{float(lon)}",
        "d": float(radio_km),  # en km (distanceUnits=kilometers en el esquema)
        "fq": ["{!geofilt}", *filtros_atributos(filtros)],
        "sort": "geodist() asc",                 # del más cercano al más lejano
        "fl": f"{FL},dist:geodist()",            # distancia de cada registro, en km
        "rows": filas,
    }


def poligono(vertices: list[list[float]], filtros: dict, filas: int) -> dict:
    """12. Registros dentro del polígono dibujado.

    `vertices`: [[lat, lon], [lat, lon], ...] en el orden en que se hicieron
    clic (mínimo 3, sin repetir el primero al final). Ojo: WKT usa «lon lat».
    """
    return {
        "q": "*:*",
        "fq": [filtro_poligono(vertices), *filtros_atributos(filtros)],
        "fl": FL,
        "rows": filas,
    }


def poligono_facets(vertices: list[list[float]], campo_facet: str, filtros: dict, filas: int) -> dict:
    """13. Mismo filtro que `poligono` + un facet sobre `campo_facet`
    (p. ej. "orden") con los registros que quedaron dentro.
    """
    params = poligono(vertices, filtros, filas)
    # Los facets se calculan sobre el resultado ya filtrado (q + fq), así que
    # los conteos corresponden solo a lo que hay dentro del polígono.
    params.update({
        "facet": "true",
        "facet.field": campo_permitido(campo_facet or "orden", CATEGORICOS),
        "facet.limit": -1,      # todas las categorías presentes
        "facet.mincount": 1,    # sin categorías vacías
        "facet.sort": "count",
    })
    return params
