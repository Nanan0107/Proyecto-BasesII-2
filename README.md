# Proyecto Bases de Datos II — Insectos en áreas protegidas de Costa Rica

Investigación de la población de insectos en las áreas silvestres protegidas (ASP) de
Costa Rica. Se combinan las ocurrencias de insectos de **GBIF «Insecta of Costa Rica
(INBio)»** con las **áreas silvestres protegidas del SINAC**.

- **Etapa 1** — ETL, imputación, anomalías e integración con Apache Spark + Sedona (`etl/etl_insectos.ipynb`).
- **Etapa 2** — Aplicación de consultas y visualización sobre Apache Solr (`backend/`, `frontend/`).

## Estructura

```
docker-compose.yml      Solr 9.7 (un nodo) con el core «insectos» + servicio «spark» (perfil etl)
etl/
  descargar_datos.py    Descarga los datos crudos (GBIF + SINAC) en datos/crudos/
  etl_insectos.ipynb    Notebook de la Etapa 1, ejecutado (Spark 3.5 + Sedona 1.9)
  Dockerfile            JupyterLab + PySpark + Sedona (Java 17, Python 3.12)
solr/
  Dockerfile            Imagen solr:9.7 + librería JTS (polígonos)
  crear_esquema.py      Esquema vía Schema API (incluye el campo espacial RPT + JTS)
  indexar.py            Carga a Solr por lotes (carpeta de Spark, JSONL[.gz] o CSV)
datos/
  crudos/               Datos originales descargados (ignorado por git)
  trabajo/              Parquet intermedios del ETL (ignorado por git)
  limpios/              Salida del ETL para Solr: insectos_asp/part-*.json.gz
  generar_muestra.py    Dataset sintético de muestra (solo para desarrollo)
backend/                API FastAPI (Python)
  app/main.py           Rutas REST
  app/solr.py           Cliente Solr: ejecuta parámetros y normaliza la respuesta
  app/catalogo.py       Las 13 consultas: formularios y visualización
  app/consultas/        Construcción de las consultas Solr (convencionales y geoespaciales)
  tests/                Pruebas contra el Solr real
frontend/               React + Vite + Leaflet + Recharts
docs/latex/            Documentación de la aplicación, consultas y pruebas (aplicacion.tex → .pdf)
docs/img/              Capturas de pantalla usadas en la documentación
```

## Etapa 1 — ETL con Spark

```bash
python3 etl/descargar_datos.py                                   # ~100 MB de GBIF + capa del SINAC
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose --profile etl build spark
docker compose --profile etl up -d spark                         # JupyterLab en http://localhost:8888
```
Abrir `etl/etl_insectos.ipynb` y ejecutar todas las celdas (≈6 min, `SPARK_DRIVER_MEMORY=6g` por defecto), o
sin interfaz:
```bash
docker compose --profile etl run --rm spark \
  jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 etl/etl_insectos.ipynb
```
Genera `datos/limpios/insectos_asp/` (3 276 325 documentos). Ver `datos/limpios/README.md`.

## Etapa 2 — Cómo ejecutar

Requisitos: Docker, Python 3.12, Node 18+.

```bash
docker compose up -d --build
```
```bash
python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt
```
```bash
backend/.venv/bin/python solr/crear_esquema.py
```
```bash
backend/.venv/bin/python solr/indexar.py datos/limpios/insectos_asp --borrar
```
(Para desarrollar sin el ETL: `python3 datos/generar_muestra.py` e indexar
`datos/muestra/insectos_muestra.jsonl`.)
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
Spark exporta estos nombres de campo (JSON Lines comprimido).

| Campo | Tipo Solr | Origen |
|---|---|---|
| `id` | string | `occurrenceID` del INBio (`urn:catalog:INB:…`) |
| `nombre_cientifico` | text_general (+ copia `nombre_cientifico_exacto` string) | GBIF |
| `orden`, `familia`, `genero`, `especie`, `rango_taxonomico` | string | GBIF |
| `fecha_evento` | pdate | inicio del rango `eventDate` |
| `anio`, `mes` | pint | `eventDate` |
| `elevacion_m` | pdouble | punto medio de elevación mín./máx. (imputada por mediana espacial si falta) |
| `provincia`, `canton`, `etapa_vida`, `sexo`, `protocolo_muestreo`, `recolector` | string | GBIF |
| `localidad` | text_general | GBIF |
| `latitud`, `longitud` | pdouble | GBIF |
| `ubicacion` | `ubicacion_rpt` (SpatialRecursivePrefixTreeFieldType + JTS), `"lat,lon"` | GBIF |
| `dentro_asp` | boolean | join espacial con SINAC |
| `area_protegida`, `categoria_manejo` | string | SINAC (con tildes restauradas) |
| `area_conservacion` | string | SINAC (siglas: ACG, ACOSA, …) |
| `area_protegida_km2` | pdouble | SINAC (área total del ASP) |
| `piso_altitudinal`, `estacion` | string | variables derivadas |
| `texto` | text_es (copyField: nombre, orden, familia, localidad, área, categoría) | — |

Registros sin área protegida: `dentro_asp=false`, `area_protegida="Fuera de ASP"`.

## Datos de muestra

`datos/generar_muestra.py` produce datos **sintéticos** con ese esquema (áreas protegidas
y taxones reales, coordenadas y fechas aleatorias). Es reproducible (`--semilla`). Sirve
solo para desarrollar; se reemplaza por la salida del notebook de Spark.
