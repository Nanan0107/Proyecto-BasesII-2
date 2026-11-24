from __future__ import annotations

from datetime import date

from ..catalogo import CAMPOS_CATEGORICOS, ORDENAMIENTOS

CAMPOS_ANALIZADOS = {"texto", "nombre_cientifico"}
CAMPOS_EXACTOS = {"familia", "area_protegida", "provincia"}
# Campos y ordenamientos que el usuario puede elegir en los formularios.
CATEGORICOS = {c["valor"] for c in CAMPOS_CATEGORICOS}
SORTS = {o["valor"] for o in ORDENAMIENTOS}
MAX_INTERVALOS = 500  # tope de barras en un range facet


def comillas(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

def quitaComillas(s: str) -> str:
    return s[1:-1]

def busqueda_texto(p: dict) -> dict:
    texto = (p.get("texto") or "").strip()
    campo = p.get("campo") or "texto"

    if campo not in CAMPOS_ANALIZADOS | CAMPOS_EXACTOS:
        raise ValueError(f"Campo no permitido: {campo}")

    if not texto:
        return {"q": "*:*"}

    if campo in CAMPOS_ANALIZADOS:
        return {"q": texto, "defType": "edismax", "qf": campo, "q.op": "AND"}

    return {"q": "*:*", "fq": [f"{campo}:{comillas(texto)}"]}


# ----------------------------------------------------------------- utilidades
def vacio(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip()) or v == []


def campo_permitido(campo: str, permitidos: set[str]) -> str:
    if campo not in permitidos:
        raise ValueError(f"Campo no permitido: {campo}")
    return campo


def igual(campo: str, valor) -> str:
    """Condición de coincidencia exacta sobre un campo string: campo:"valor"."""
    return f"{campo}:{comillas(str(valor).strip())}"


def numero(v, entero: bool = False):
    """Convierte el valor del formulario a número (ValueError si no lo es)."""
    n = float(v)
    return int(n) if entero or n.is_integer() else n


def entero_positivo(v, por_defecto: int) -> int:
    return max(1, int(float(v))) if not vacio(v) else por_defecto


def fecha_solr(v: str, fin_del_dia: bool) -> str:
    """"AAAA-MM-DD" → formato de fecha de Solr (ISO 8601 en UTC)."""
    d = date.fromisoformat(str(v).strip())  # valida el formato
    return f"{d.isoformat()}T23:59:59.999Z" if fin_del_dia else f"{d.isoformat()}T00:00:00Z"


METRICAS_ELEVACION = {
    "elev_promedio": "avg(elevacion_m)",
    "elev_min": "min(elevacion_m)",
    "elev_max": "max(elevacion_m)",
    "especies_distintas": "unique(especie)",
}


def operadores_logicos(p: dict) -> dict:
    obligatorias = []
    if not vacio(p.get("orden")):
        obligatorias.append(igual("orden", p["orden"]))

    categorias = [c for c in (p.get("categorias") or []) if not vacio(c)]
    if categorias:
        # OR: basta con que cumpla una de las categorías
        opciones = " OR ".join(comillas(c.strip()) for c in categorias)
        obligatorias.append(f"categoria_manejo:({opciones})")

    # AND: todas las condiciones obligatorias deben cumplirse
    q = " AND ".join(obligatorias) if obligatorias else "*:*"

    if not vacio(p.get("excluir_provincia")):
        # NOT: excluye los documentos de esa provincia
        q = f"({q}) NOT {igual('provincia', p['excluir_provincia'])}"

    # Se arma todo en q (parser estándar de Lucene) para que los tres
    # operadores se vean juntos en una sola expresión booleana.
    return {"q": q}


def rangos(p: dict) -> dict:
    """3. Rango numérico (elevación) y temporal (fecha de colecta).

    p["elev_min"], p["elev_max"]: números (metros).
    p["fecha_desde"], p["fecha_hasta"]: "AAAA-MM-DD" (fecha_evento es pdate).
    """
    fq = []

    # Rango numérico inclusivo [a TO b]; un extremo vacío queda abierto (*).
    lo = "*" if vacio(p.get("elev_min")) else numero(p["elev_min"])
    hi = "*" if vacio(p.get("elev_max")) else numero(p["elev_max"])
    if (lo, hi) != ("*", "*"):
        fq.append(f"elevacion_m:[{lo} TO {hi}]")

    # Rango temporal: desde el inicio del primer día hasta el final del último.
    desde = "*" if vacio(p.get("fecha_desde")) else fecha_solr(p["fecha_desde"], fin_del_dia=False)
    hasta = "*" if vacio(p.get("fecha_hasta")) else fecha_solr(p["fecha_hasta"], fin_del_dia=True)
    if (desde, hasta) != ("*", "*"):
        fq.append(f"fecha_evento:[{desde} TO {hasta}]")

    return {"q": "*:*", "fq": fq, "sort": "fecha_evento asc"}


def filtros_y_orden(p: dict) -> dict:
    """4. Varios filtros opcionales combinados + ordenamiento por dos atributos.

    p["orden"], p["area_conservacion"], p["etapa_vida"], p["estacion"]: opcionales.
    p["orden_1"]: p. ej. "fecha_evento desc"; p["orden_2"]: opcional.
    """
    # Cada filtro no vacío es un fq aparte: Solr los combina con AND y
    # guarda cada uno en la caché de filtros por separado.
    fq = [igual(campo, p[campo])
          for campo in ("orden", "area_conservacion", "etapa_vida", "estacion")
          if not vacio(p.get(campo))]

    criterios = []
    for clave in ("orden_1", "orden_2"):
        valor = p.get(clave)
        if vacio(valor):
            continue
        if valor not in SORTS:
            raise ValueError(f"Ordenamiento no permitido: {valor}")
        if valor.split()[0] not in [c.split()[0] for c in criterios]:
            criterios.append(valor)
    # Desempate final por id: el orden queda estable al paginar.
    criterios.append("id asc")

    return {"q": "*:*", "fq": fq, "sort": ", ".join(criterios)}


def facet_por_campo(p: dict) -> dict:
    """5. Field facet: conteo de registros por cada valor de p["campo"].

    p["limite"]: máximo de valores; p["minimo"]: conteo mínimo para aparecer.
    """
    campo = campo_permitido(p.get("campo") or "orden", CATEGORICOS)
    return {
        "q": "*:*",
        "rows": 0,                 # solo interesan los conteos, no los documentos
        "facet": "true",
        "facet.field": campo,
        "facet.limit": entero_positivo(p.get("limite"), 10),
        "facet.mincount": 0 if vacio(p.get("minimo")) else max(0, int(float(p["minimo"]))),
        "facet.sort": "count",     # de mayor a menor cantidad de registros
    }


def facet_por_rango(p: dict) -> dict:
    """6. Range facet: conteo por intervalos de p["campo"] ("elevacion_m" o "anio").

    p["inicio"], p["fin"], p["intervalo"]: números.
    """
    campo = campo_permitido(p.get("campo") or "elevacion_m", {"elevacion_m", "anio"})
    entero = campo == "anio"  # anio es pint: los límites deben ser enteros
    inicio = numero(p.get("inicio", 0), entero)
    fin = numero(p.get("fin", 3500), entero)
    intervalo = numero(p.get("intervalo", 250), entero)
    if intervalo <= 0 or fin <= inicio:
        raise ValueError("Se requiere intervalo > 0 y «hasta» mayor que «desde»")
    if (fin - inicio) / intervalo > MAX_INTERVALOS:
        raise ValueError(f"Demasiados intervalos (máximo {MAX_INTERVALOS})")
    return {
        "q": "*:*",
        "rows": 0,
        "facet": "true",
        "facet.range": campo,
        "facet.range.start": inicio,
        "facet.range.end": fin,
        "facet.range.gap": intervalo,
        "facet.mincount": 0,           # muestra también los intervalos vacíos
        "facet.range.other": "all",    # cuenta lo que queda antes/después del rango
    }


def facet_por_consultas(p: dict) -> dict:
    """7. Query facets: un conteo por cada condición que ustedes definan
    (mínimo 3; p. ej. pisos altitudinales por rango de elevación, dentro vs.
    fuera de un ASP, estación seca vs. lluviosa).

    p["orden"]: opcional, limita todo el análisis a un orden.
    """
    # Cada facet.query es una condición independiente; {!key=...} le da un
    # nombre legible al conteo. Los rangos de elevación usan "}" (exclusivo)
    # en el extremo superior para que un registro no caiga en dos pisos.
    condiciones = [
        ("Piso basal (< 500 m)", "elevacion_m:[* TO 500}"),
        ("Piso premontano (500–1500 m)", "elevacion_m:[500 TO 1500}"),
        ("Piso montano bajo (1500–2500 m)", "elevacion_m:[1500 TO 2500}"),
        ("Piso montano (≥ 2500 m)", "elevacion_m:[2500 TO *]"),
        ("Dentro de un ASP", "dentro_asp:true"),
        ("Fuera de un ASP", "dentro_asp:false"),
        ("Estación seca (dic–abr)", 'estacion:"Seca"'),
        ("Estación lluviosa (may–nov)", 'estacion:"Lluviosa"'),
    ]
    fq = [] if vacio(p.get("orden")) else [igual("orden", p["orden"])]
    return {
        "q": "*:*",
        "fq": fq,
        "rows": 0,
        "facet": "true",
        "facet.query": [f"{{!key='{nombre}'}}{condicion}" for nombre, condicion in condiciones],
    }


def facet_anidado(p: dict) -> dict:
    """8. Facets anidados: para cada valor de p["campo_padre"], la distribución
    de p["campo_hijo"].

    p["limite_padre"], p["limite_hijo"]: máximos por nivel.
    """
    padre = campo_permitido(p.get("campo_padre") or "area_conservacion", CATEGORICOS)
    hijo = campo_permitido(p.get("campo_hijo") or "orden", CATEGORICOS)
    if padre == hijo:
        raise ValueError("Los dos niveles deben ser campos distintos")
    # JSON Facet API: un facet "terms" dentro de cada bucket de otro facet
    # "terms". Cada nivel tiene su propio límite y orden.
    return {
        "q": "*:*",
        "rows": 0,
        "json.facet": {
            padre: {
                "type": "terms",
                "field": padre,
                "limit": entero_positivo(p.get("limite_padre"), 12),
                "sort": "count desc",
                "facet": {
                    hijo: {
                        "type": "terms",
                        "field": hijo,
                        "limit": entero_positivo(p.get("limite_hijo"), 5),
                        "sort": "count desc",
                    },
                },
            },
        },
    }


def facet_estadisticas(p: dict) -> dict:
    """9. Facets con funciones estadísticas: por cada valor de p["campo_grupo"],
    al menos promedio, mínimo y máximo de elevacion_m (y, si quieren, cantidad
    de especies distintas o una suma).

    p["limite"]: máximo de grupos.
    """
    campo = campo_permitido(p.get("campo_grupo") or "area_protegida", CATEGORICOS)
    # Dentro de cada bucket, funciones de agregación de la JSON Facet API:
    # avg, min, max y unique (cantidad de valores distintos).
    return {
        "q": "*:*",
        "rows": 0,
        "json.facet": {
            campo: {
                "type": "terms",
                "field": campo,
                "limit": entero_positivo(p.get("limite"), 15),
                "sort": "count desc",
                "facet": dict(METRICAS_ELEVACION),
            },
        },
    }


def ranking_especies(p: dict) -> dict:
    """10. Especies más registradas dentro de p["area_protegida"], junto con
    alguna estadística del área (p. ej. elevación mínima y máxima).

    p["limite"]: cantidad de especies del ranking.
    """
    if vacio(p.get("area_protegida")):
        raise ValueError("Seleccione un área protegida")
    return {
        "q": "*:*",
        # El filtro limita todo (ranking y estadísticas) al área elegida.
        "fq": [igual("area_protegida", p["area_protegida"])],
        "rows": 0,
        "json.facet": {
            # Ranking: terms sobre "especie", que solo existe en los registros
            # identificados hasta especie (los de género o familia no cuentan).
            "especies": {
                "type": "terms",
                "field": "especie",
                "limit": entero_positivo(p.get("limite"), 10),
                "sort": "count desc",
                "facet": {"elev_promedio": "avg(elevacion_m)"},
            },
            # Estadísticas globales del área (fuera de cualquier bucket).
            **METRICAS_ELEVACION,
        },
    }
