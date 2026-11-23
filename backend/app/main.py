"""API REST de la aplicación de consultas sobre Apache Solr.

Ejecutar (desde backend/):
    .venv/bin/uvicorn app.main:app --reload --port 8000
Documentación interactiva: http://localhost:8000/docs
"""

from __future__ import annotations

import os
from typing import Any, Callable

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from . import catalogo, solr
from .consultas import convencionales, geoespaciales

app = FastAPI(title="Insectos en áreas protegidas de Costa Rica — API Solr", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

CAMPOS_MAPA = ["id", "latitud", "longitud"]
FL_MAPA = "id,latitud,longitud,nombre_cientifico,orden,area_protegida,elevacion_m,fecha_evento"
MAX_FILAS = 5000


# --------------------------------------------------------------------- modelos
class EjecutarConsulta(BaseModel):
    parametros: dict[str, Any] = Field(default_factory=dict)
    pagina: int = Field(0, ge=0)
    filas: int = Field(20, ge=0, le=200)


class Filtros(BaseModel):
    orden: str | None = None

    def como_dict(self) -> dict:
        return {k: v for k, v in self.model_dump().items() if v not in (None, "")}


class Proximidad(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    radio_km: float = Field(..., gt=0, le=500)
    filtros: Filtros = Field(default_factory=Filtros)
    filas: int = Field(1000, ge=0, le=MAX_FILAS)


class Poligono(BaseModel):
    vertices: list[list[float]]
    filtros: Filtros = Field(default_factory=Filtros)
    filas: int = Field(1000, ge=0, le=MAX_FILAS)
    campo_facet: str = "orden"

    @field_validator("vertices")
    @classmethod
    def validar_vertices(cls, v: list[list[float]]) -> list[list[float]]:
        if len(v) < 3:
            raise ValueError("El polígono necesita al menos 3 vértices")
        for punto in v:
            if len(punto) != 2 or not (-90 <= punto[0] <= 90 and -180 <= punto[1] <= 180):
                raise ValueError(f"Vértice inválido: {punto} (se espera [lat, lon])")
        return v


# ------------------------------------------------------------------- ejecución
def _correr(construir: Callable[[], dict], ajustar: Callable[[dict], None] | None = None) -> dict:
    """Llama a la función de Fabián, completa los parámetros y ejecuta en Solr."""
    try:
        params = construir()
    except NotImplementedError:
        raise HTTPException(501, "Consulta pendiente de implementar (ver docs/guia-solr.md).")
    except Exception as e:  # error de programación en la función de la consulta
        raise HTTPException(500, f"Error al construir la consulta: {type(e).__name__}: {e}")
    if not isinstance(params, dict):
        raise HTTPException(500, "La función de la consulta debe devolver un dict de parámetros Solr.")
    params = dict(params)
    params.setdefault("q", "*:*")
    if ajustar:
        ajustar(params)
    try:
        return solr.ejecutar(params)
    except solr.SolrError as e:
        raise HTTPException(e.status, {"mensaje": e.mensaje, "solr_params": e.params})


def _asegurar_campos_mapa(params: dict) -> None:
    fl = params.get("fl")
    if fl and fl.strip() != "*":
        campos = [c.strip() for c in fl.split(",")]
        faltan = [c for c in CAMPOS_MAPA if c not in campos]
        if faltan:
            params["fl"] = ",".join(campos + faltan)


# ---------------------------------------------------------------------- rutas
@app.get("/api/estado")
def estado() -> dict:
    return solr.ping()


@app.get("/api/catalogo")
def obtener_catalogo() -> dict:
    return {"grupos": catalogo.GRUPOS, "consultas": catalogo.CONSULTAS}


@app.get("/api/opciones")
def opciones() -> dict:
    """Valores de los campos categóricos para llenar los menús de la interfaz."""
    params = {"q": "*:*", "rows": 0, "facet": "true", "facet.field": catalogo.CAMPOS_OPCIONES,
              "facet.limit": 200, "facet.mincount": 1, "facet.sort": "index"}
    try:
        r = solr.ejecutar(params)
    except solr.SolrError as e:
        raise HTTPException(e.status, e.mensaje)
    return {f["nombre"]: [b["valor"] for b in f["buckets"]] for f in r["facets"]}


@app.post("/api/consultas/{consulta_id}")
def ejecutar_consulta(consulta_id: int, cuerpo: EjecutarConsulta) -> dict:
    meta = catalogo.POR_ID.get(consulta_id)
    if not meta or meta["grupo"] == "geo":
        raise HTTPException(404, f"No existe la consulta convencional {consulta_id}")
    funcion = getattr(convencionales, meta["funcion"])
    p = {**catalogo.valores_por_defecto(meta), **cuerpo.parametros}

    def ajustar(params: dict) -> None:
        params.setdefault("rows", cuerpo.filas)
        params["start"] = cuerpo.pagina * cuerpo.filas

    return _correr(lambda: funcion(p), ajustar)


@app.get("/api/mapa/puntos")
def puntos_mapa(orden: str | None = None, filas: int = 2000) -> dict:
    """Muestra de puntos para la vista inicial del mapa (sin filtro espacial)."""
    params: dict[str, Any] = {"q": "*:*", "fl": FL_MAPA, "rows": min(filas, MAX_FILAS),
                              "sort": "random_2026 asc"}
    if orden:
        params["fq"] = f'orden:"{orden}"'
    try:
        return solr.ejecutar(params)
    except solr.SolrError as e:
        raise HTTPException(e.status, e.mensaje)


@app.post("/api/geo/proximidad")
def geo_proximidad(c: Proximidad) -> dict:
    return _correr(lambda: geoespaciales.proximidad(c.lat, c.lon, c.radio_km, c.filtros.como_dict(), c.filas),
                   _asegurar_campos_mapa)


@app.post("/api/geo/poligono")
def geo_poligono(c: Poligono) -> dict:
    return _correr(lambda: geoespaciales.poligono(c.vertices, c.filtros.como_dict(), c.filas),
                   _asegurar_campos_mapa)


@app.post("/api/geo/poligono-facets")
def geo_poligono_facets(c: Poligono) -> dict:
    return _correr(lambda: geoespaciales.poligono_facets(c.vertices, c.campo_facet, c.filtros.como_dict(),
                                                         c.filas),
                   _asegurar_campos_mapa)
