"""Consultas convencionales y facets — LAS ESCRIBE FABIÁN.

Contrato (igual para todas las funciones):
    - Reciben `p`: dict con los valores del formulario de la interfaz
      (los nombres de las claves están en app/catalogo.py, campo "formulario").
      Un campo opcional vacío llega como "" o None.
    - Devuelven un dict con los parámetros de Solr, por ejemplo:
          {"q": "...", "fq": ["...", "..."], "sort": "...", "fl": "...",
           "rows": 0, "facet": "true", "facet.field": "...",
           "json.facet": {...}}
      * Una lista se envía como parámetro repetido (fq=a&fq=b).
      * Un dict (json.facet) se convierte a JSON automáticamente.
      * Si no ponen "rows", la API usa el tamaño de página de la interfaz;
        "start" (paginación) lo pone la API.
    - NO hacen la petición HTTP: app/solr.py la ejecuta y normaliza la respuesta.
    - Mientras una función lance NotImplementedError, la interfaz la muestra
      como «pendiente de implementar».

Guía paso a paso: docs/guia-solr.md (Paso 3).
Pruebas: backend/.venv/bin/pytest backend/tests -k consulta_N
"""

from __future__ import annotations


def busqueda_texto(p: dict) -> dict:
    """1. Búsqueda por texto o categoría.

    p["texto"]: lo que escribió el usuario.
    p["campo"]: "texto" (búsqueda general, campo analizado), "nombre_cientifico"
                (analizado), o "familia" / "area_protegida" / "provincia"
                (campos string: coincidencia exacta).
    """
    raise NotImplementedError


def operadores_logicos(p: dict) -> dict:
    """2. AND, OR y NOT en una misma consulta.

    p["orden"]: un orden (debe cumplirse: AND).
    p["categorias"]: lista de categorías de manejo (basta una: OR).
    p["excluir_provincia"]: provincia que NO debe aparecer (NOT).
    """
    raise NotImplementedError


def rangos(p: dict) -> dict:
    """3. Rango numérico (elevación) y temporal (fecha de colecta).

    p["elev_min"], p["elev_max"]: números (metros).
    p["fecha_desde"], p["fecha_hasta"]: "AAAA-MM-DD" (fecha_evento es pdate).
    """
    raise NotImplementedError


def filtros_y_orden(p: dict) -> dict:
    """4. Varios filtros opcionales combinados + ordenamiento por dos atributos.

    p["orden"], p["area_conservacion"], p["etapa_vida"], p["estacion"]: opcionales.
    p["orden_1"]: p. ej. "fecha_evento desc"; p["orden_2"]: opcional.
    """
    raise NotImplementedError


def facet_por_campo(p: dict) -> dict:
    """5. Field facet: conteo de registros por cada valor de p["campo"].

    p["limite"]: máximo de valores; p["minimo"]: conteo mínimo para aparecer.
    """
    raise NotImplementedError


def facet_por_rango(p: dict) -> dict:
    """6. Range facet: conteo por intervalos de p["campo"] ("elevacion_m" o "anio").

    p["inicio"], p["fin"], p["intervalo"]: números.
    """
    raise NotImplementedError


def facet_por_consultas(p: dict) -> dict:
    """7. Query facets: un conteo por cada condición que ustedes definan
    (mínimo 3; p. ej. pisos altitudinales por rango de elevación, dentro vs.
    fuera de un ASP, estación seca vs. lluviosa).

    p["orden"]: opcional, limita todo el análisis a un orden.
    """
    raise NotImplementedError


def facet_anidado(p: dict) -> dict:
    """8. Facets anidados: para cada valor de p["campo_padre"], la distribución
    de p["campo_hijo"].

    p["limite_padre"], p["limite_hijo"]: máximos por nivel.
    """
    raise NotImplementedError


def facet_estadisticas(p: dict) -> dict:
    """9. Facets con funciones estadísticas: por cada valor de p["campo_grupo"],
    al menos promedio, mínimo y máximo de elevacion_m (y, si quieren, cantidad
    de especies distintas o una suma).

    p["limite"]: máximo de grupos.
    """
    raise NotImplementedError


def ranking_especies(p: dict) -> dict:
    """10. Especies más registradas dentro de p["area_protegida"], junto con
    alguna estadística del área (p. ej. elevación mínima y máxima).

    p["limite"]: cantidad de especies del ranking.
    """
    raise NotImplementedError
