"""Catálogo de consultas que ofrece la aplicación.

Cada entrada describe una consulta para la interfaz: su grupo, el requisito
del enunciado que cubre, el formulario que se muestra y cómo se visualiza el
resultado. La lógica Solr de cada una está en app/consultas/.

Tipos de campo del formulario:
    texto, numero, fecha, seleccion, multiseleccion
`opciones_de` indica un campo de Solr cuyos valores (field facet) llenan el menú.
`opciones` es una lista fija de {valor, etiqueta}.
`opcional`: True si el campo puede quedar vacío.

Visualizaciones: tabla, barras, histograma, anidado, estadisticas.
"""

from __future__ import annotations

CAMPOS_CATEGORICOS = [
    {"valor": "orden", "etiqueta": "Orden"},
    {"valor": "familia", "etiqueta": "Familia"},
    {"valor": "area_protegida", "etiqueta": "Área protegida"},
    {"valor": "categoria_manejo", "etiqueta": "Categoría de manejo"},
    {"valor": "area_conservacion", "etiqueta": "Área de conservación"},
    {"valor": "provincia", "etiqueta": "Provincia"},
    {"valor": "piso_altitudinal", "etiqueta": "Piso altitudinal"},
    {"valor": "estacion", "etiqueta": "Estación"},
    {"valor": "protocolo_muestreo", "etiqueta": "Protocolo de muestreo"},
    {"valor": "etapa_vida", "etiqueta": "Etapa de vida"},
]

ORDENAMIENTOS = [
    {"valor": "fecha_evento desc", "etiqueta": "Fecha (más reciente primero)"},
    {"valor": "fecha_evento asc", "etiqueta": "Fecha (más antigua primero)"},
    {"valor": "elevacion_m desc", "etiqueta": "Elevación (mayor primero)"},
    {"valor": "elevacion_m asc", "etiqueta": "Elevación (menor primero)"},
    {"valor": "nombre_cientifico_exacto asc", "etiqueta": "Nombre científico (A-Z)"},
    {"valor": "area_protegida asc", "etiqueta": "Área protegida (A-Z)"},
]

GRUPOS = [
    {"id": "busqueda", "titulo": "Búsqueda y filtrado"},
    {"id": "facets", "titulo": "Agregaciones (facets)"},
    {"id": "geo", "titulo": "Geoespaciales"},
]

CONSULTAS = [
    # ------------------------------------------------------------- a. búsqueda
    {
        "id": 1, "grupo": "busqueda", "funcion": "busqueda_texto",
        "titulo": "Búsqueda por texto o categoría",
        "requisito": "Búsqueda por valores de campos textuales o categóricos",
        "descripcion": "Encuentra registros por nombre científico, familia, área protegida o texto libre.",
        "visualizacion": "tabla",
        "formulario": [
            {"nombre": "texto", "etiqueta": "Buscar", "tipo": "texto", "por_defecto": "Morpho"},
            {"nombre": "campo", "etiqueta": "Buscar en", "tipo": "seleccion", "por_defecto": "texto",
             "opciones": [{"valor": "texto", "etiqueta": "Todo (texto general)"},
                          {"valor": "nombre_cientifico", "etiqueta": "Nombre científico"},
                          {"valor": "familia", "etiqueta": "Familia (exacto)"},
                          {"valor": "area_protegida", "etiqueta": "Área protegida (exacto)"},
                          {"valor": "provincia", "etiqueta": "Provincia (exacto)"}]},
        ],
    },
    {
        "id": 2, "grupo": "busqueda", "funcion": "operadores_logicos",
        "titulo": "Operadores lógicos (AND, OR, NOT)",
        "requisito": "Consultas con operadores lógicos AND, OR y NOT",
        "descripcion": "Registros de un orden en ciertas categorías de manejo, excluyendo una provincia.",
        "visualizacion": "tabla",
        "formulario": [
            {"nombre": "orden", "etiqueta": "Orden (AND)", "tipo": "seleccion", "opciones_de": "orden",
             "por_defecto": "Lepidoptera"},
            {"nombre": "categorias", "etiqueta": "Categorías de manejo (OR)", "tipo": "multiseleccion",
             "opciones_de": "categoria_manejo", "por_defecto": ["Parque Nacional", "Reserva Biológica"]},
            {"nombre": "excluir_provincia", "etiqueta": "Excluir provincia (NOT)", "tipo": "seleccion",
             "opciones_de": "provincia", "por_defecto": "Limón"},
        ],
    },
    {
        "id": 3, "grupo": "busqueda", "funcion": "rangos",
        "titulo": "Rangos de elevación y fecha",
        "requisito": "Consultas por rangos numéricos o temporales",
        "descripcion": "Registros colectados entre dos elevaciones y dentro de un periodo.",
        "visualizacion": "tabla",
        "formulario": [
            {"nombre": "elev_min", "etiqueta": "Elevación mínima (m)", "tipo": "numero", "por_defecto": 1000},
            {"nombre": "elev_max", "etiqueta": "Elevación máxima (m)", "tipo": "numero", "por_defecto": 2500},
            {"nombre": "fecha_desde", "etiqueta": "Desde", "tipo": "fecha", "por_defecto": "1995-01-01"},
            {"nombre": "fecha_hasta", "etiqueta": "Hasta", "tipo": "fecha", "por_defecto": "2005-12-31"},
        ],
    },
    {
        "id": 4, "grupo": "busqueda", "funcion": "filtros_y_orden",
        "titulo": "Filtros combinados y ordenamiento",
        "requisito": "Combinación de condiciones mediante filtros y ordenamiento por uno o varios atributos",
        "descripcion": "Combina varios filtros opcionales y ordena por dos criterios.",
        "visualizacion": "tabla",
        "formulario": [
            {"nombre": "orden", "etiqueta": "Orden", "tipo": "seleccion", "opciones_de": "orden",
             "opcional": True, "por_defecto": "Coleoptera"},
            {"nombre": "area_conservacion", "etiqueta": "Área de conservación", "tipo": "seleccion",
             "opciones_de": "area_conservacion", "opcional": True, "por_defecto": "ACOSA"},
            {"nombre": "etapa_vida", "etiqueta": "Etapa de vida", "tipo": "seleccion",
             "opciones_de": "etapa_vida", "opcional": True, "por_defecto": ""},
            {"nombre": "estacion", "etiqueta": "Estación", "tipo": "seleccion",
             "opciones_de": "estacion", "opcional": True, "por_defecto": ""},
            {"nombre": "orden_1", "etiqueta": "Ordenar por", "tipo": "seleccion", "opciones": ORDENAMIENTOS,
             "por_defecto": "fecha_evento desc"},
            {"nombre": "orden_2", "etiqueta": "Luego por", "tipo": "seleccion", "opciones": ORDENAMIENTOS,
             "opcional": True, "por_defecto": "elevacion_m asc"},
        ],
    },
    # --------------------------------------------------------------- b. facets
    {
        "id": 5, "grupo": "facets", "funcion": "facet_por_campo",
        "titulo": "Conteo por categoría (field facet)",
        "requisito": "Field facets",
        "descripcion": "Cuántos registros hay por cada valor de un atributo categórico.",
        "visualizacion": "barras",
        "formulario": [
            {"nombre": "campo", "etiqueta": "Agrupar por", "tipo": "seleccion", "opciones": CAMPOS_CATEGORICOS,
             "por_defecto": "orden"},
            {"nombre": "limite", "etiqueta": "Máximo de categorías", "tipo": "numero", "por_defecto": 10},
            {"nombre": "minimo", "etiqueta": "Conteo mínimo", "tipo": "numero", "por_defecto": 1},
        ],
    },
    {
        "id": 6, "grupo": "facets", "funcion": "facet_por_rango",
        "titulo": "Distribución por intervalos (range facet)",
        "requisito": "Range facets",
        "descripcion": "Registros por franjas de elevación o por año de colecta.",
        "visualizacion": "histograma",
        "formulario": [
            {"nombre": "campo", "etiqueta": "Variable", "tipo": "seleccion", "por_defecto": "elevacion_m",
             "opciones": [{"valor": "elevacion_m", "etiqueta": "Elevación (m)"},
                          {"valor": "anio", "etiqueta": "Año de colecta"}]},
            {"nombre": "inicio", "etiqueta": "Desde", "tipo": "numero", "por_defecto": 0},
            {"nombre": "fin", "etiqueta": "Hasta", "tipo": "numero", "por_defecto": 3500},
            {"nombre": "intervalo", "etiqueta": "Tamaño del intervalo", "tipo": "numero", "por_defecto": 250},
        ],
    },
    {
        "id": 7, "grupo": "facets", "funcion": "facet_por_consultas",
        "titulo": "Conteo por condiciones (query facets)",
        "requisito": "Query facets",
        "descripcion": "Cuántos registros cumplen cada condición: pisos altitudinales, dentro/fuera de ASP, estación.",
        "visualizacion": "barras",
        "formulario": [
            {"nombre": "orden", "etiqueta": "Limitar a un orden", "tipo": "seleccion", "opciones_de": "orden",
             "opcional": True, "por_defecto": ""},
        ],
    },
    {
        "id": 8, "grupo": "facets", "funcion": "facet_anidado",
        "titulo": "Distribución cruzada (facets anidados)",
        "requisito": "Facets anidados",
        "descripcion": "Para cada valor del primer atributo, la distribución del segundo.",
        "visualizacion": "anidado",
        "formulario": [
            {"nombre": "campo_padre", "etiqueta": "Primer nivel", "tipo": "seleccion",
             "opciones": CAMPOS_CATEGORICOS, "por_defecto": "area_conservacion"},
            {"nombre": "campo_hijo", "etiqueta": "Segundo nivel", "tipo": "seleccion",
             "opciones": CAMPOS_CATEGORICOS, "por_defecto": "orden"},
            {"nombre": "limite_padre", "etiqueta": "Máximo primer nivel", "tipo": "numero", "por_defecto": 12},
            {"nombre": "limite_hijo", "etiqueta": "Máximo segundo nivel", "tipo": "numero", "por_defecto": 5},
        ],
    },
    {
        "id": 9, "grupo": "facets", "funcion": "facet_estadisticas",
        "titulo": "Estadísticas por categoría",
        "requisito": "Facets con funciones estadísticas (promedio, mínimo, máximo, suma)",
        "descripcion": "Promedio, mínimo y máximo de la elevación y riqueza de especies por grupo.",
        "visualizacion": "estadisticas",
        "formulario": [
            {"nombre": "campo_grupo", "etiqueta": "Agrupar por", "tipo": "seleccion",
             "opciones": CAMPOS_CATEGORICOS, "por_defecto": "area_protegida"},
            {"nombre": "limite", "etiqueta": "Máximo de grupos", "tipo": "numero", "por_defecto": 15},
        ],
    },
    {
        "id": 10, "grupo": "facets", "funcion": "ranking_especies",
        "titulo": "Especies más registradas en un área protegida",
        "requisito": "Field facet filtrado + estadísticas del área",
        "descripcion": "Ranking de especies de un área protegida y su rango de elevación.",
        "visualizacion": "barras",
        "formulario": [
            {"nombre": "area_protegida", "etiqueta": "Área protegida", "tipo": "seleccion",
             "opciones_de": "area_protegida", "por_defecto": "Corcovado"},
            {"nombre": "limite", "etiqueta": "Cantidad de especies", "tipo": "numero", "por_defecto": 10},
        ],
    },
    # ------------------------------------------------------------ c. geoespaciales
    {
        "id": 11, "grupo": "geo", "funcion": "proximidad", "modo_mapa": "proximidad",
        "titulo": "Proximidad a un punto",
        "requisito": "Consulta por proximidad con radio definido por el usuario (+ filtro por atributo)",
        "descripcion": "Haga clic en el mapa y elija un radio: registros a esa distancia, más cercanos primero.",
        "visualizacion": "mapa",
        "formulario": [],
    },
    {
        "id": 12, "grupo": "geo", "funcion": "poligono", "modo_mapa": "poligono",
        "titulo": "Registros dentro de un polígono",
        "requisito": "Consulta por polígono dibujado por el usuario",
        "descripcion": "Dibuje un polígono de varios vértices; Solr devuelve solo los registros dentro.",
        "visualizacion": "mapa",
        "formulario": [],
    },
    {
        "id": 13, "grupo": "geo", "funcion": "poligono_facets", "modo_mapa": "poligono_facets",
        "titulo": "Polígono + facets",
        "requisito": "Filtro por polígono combinado con facets",
        "descripcion": "Distribución de los registros dentro del polígono según un atributo.",
        "visualizacion": "mapa",
        "formulario": [],
    },
]

POR_ID = {c["id"]: c for c in CONSULTAS}

# Campos cuyos valores se cargan para los menús desplegables
CAMPOS_OPCIONES = ["orden", "familia", "area_protegida", "categoria_manejo", "area_conservacion",
                   "provincia", "etapa_vida", "estacion", "piso_altitudinal", "protocolo_muestreo"]


def valores_por_defecto(consulta: dict) -> dict:
    return {c["nombre"]: c.get("por_defecto") for c in consulta["formulario"]}
