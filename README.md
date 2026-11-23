# Proyecto Bases de Datos II — Insectos en áreas protegidas de Costa Rica

Investigación de la población de insectos en las áreas silvestres protegidas (ASP) de
Costa Rica. Se combinan las ocurrencias de insectos de **GBIF «Insecta of Costa Rica
(INBio)»** con las **áreas silvestres protegidas del SINAC**.

- **Etapa 1** — ETL, imputación, anomalías e integración con Apache Spark (notebook).
- **Etapa 2** — Aplicación de consultas y visualización sobre Apache Solr (este código).

## Estructura

```
docker-compose.yml      Solr 9 con el core «insectos» (pendiente — Paso 1 de la guía)
solr/
  crear_esquema.py      Esquema vía Schema API (incluye el campo espacial RPT + JTS)
  indexar.py            Carga JSONL/CSV a Solr por lotes
datos/
  generar_muestra.py    Dataset de muestra (100 000 docs) mientras llega el de Spark
backend/                API FastAPI (Python)
  app/main.py           Rutas REST
  app/solr.py           Cliente Solr: ejecuta parámetros y normaliza la respuesta
  app/catalogo.py       Las 13 consultas: formularios y visualización
  app/consultas/        Construcción de las consultas Solr (convencionales y geoespaciales)
  tests/                Pruebas contra el Solr real
frontend/               React + Vite + Leaflet + Recharts
docs/guia-solr.md       Guía paso a paso de la parte de Solr
```

## Cómo ejecutar

Requisitos: Docker, Python 3.12, Node 18+.

```bash
docker compose up -d --build
```
```bash
python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt
```
```bash
python3 datos/generar_muestra.py
```
```bash
backend/.venv/bin/python solr/crear_esquema.py
```
```bash
backend/.venv/bin/python solr/indexar.py datos/muestra/insectos_muestra.jsonl --borrar
```
```bash
backend/.venv/bin/uvicorn app.main:app --app-dir backend --reload --port 8000
```
```bash
npm --prefix frontend install && npm --prefix frontend run dev
```

Abrir <http://localhost:5173>. Documentación interactiva de la API: <http://localhost:8000/docs>.

Pruebas:
```bash
backend/.venv/bin/pytest backend/tests -v
```

## Esquema del documento en Solr

Un documento = una ocurrencia de insecto ya unida con su área protegida. El notebook de
Spark debe exportar estos nombres de campo (JSONL o CSV).

| Campo | Tipo Solr | Origen |
|---|---|---|
| `id` | string | `gbifID` |
| `nombre_cientifico` | text_general (+ copia `nombre_cientifico_exacto` string) | GBIF |
| `orden`, `familia`, `genero`, `especie`, `rango_taxonomico` | string | GBIF |
| `fecha_evento` | pdate | `eventDate` |
| `anio`, `mes` | pint | `eventDate` |
| `elevacion_m` | pdouble | `elevation` |
| `provincia`, `canton`, `etapa_vida`, `sexo`, `protocolo_muestreo`, `recolector` | string | GBIF |
| `localidad` | text_general | GBIF |
| `latitud`, `longitud` | pdouble | GBIF |
| `ubicacion` | `ubicacion_rpt` (SpatialRecursivePrefixTreeFieldType + JTS), `"lat,lon"` | GBIF |
| `dentro_asp` | boolean | join espacial con SINAC |
| `area_protegida`, `categoria_manejo`, `area_conservacion` | string | SINAC |
| `area_protegida_km2` | pdouble | SINAC |
| `piso_altitudinal`, `estacion` | string | variables derivadas |
| `texto` | text_es (copyField: nombre, orden, familia, localidad, área, categoría) | — |

Registros sin área protegida: `dentro_asp=false`, `area_protegida="Fuera de ASP"`.

## Datos de muestra

`datos/generar_muestra.py` produce datos **sintéticos** con ese esquema (áreas protegidas
y taxones reales, coordenadas y fechas aleatorias). Es reproducible (`--semilla`). Sirve
solo para desarrollar; se reemplaza por la salida del notebook de Spark.
