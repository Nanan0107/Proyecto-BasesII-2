# Resumen del trabajo — Etapa 1 (Spark) e integración con la Etapa 2

Estado al 25/11/2026. **Nada está en commit ni subido a GitHub**: todo queda en la copia local para que lo revisen
con `git status` / `git diff`.

## 1. Estado general

| Parte | Estado |
|---|---|
| Etapa 1 — ETL con Spark (notebook ejecutado) | ✅ Completa |
| Datos limpios para Solr | ✅ 3 276 325 documentos en `datos/limpios/insectos_asp/` |
| Solr con los datos reales | ✅ Indexados (≈3 min) |
| Etapa 2 — 13 consultas (trabajo de Fabián) | ✅ Integradas y probadas con los datos reales |
| Pruebas automáticas del backend | ✅ 22 de 22 pasan con los datos reales |
| Documentación de la aplicación (LaTeX/PDF) | ✅ Cifras de los datos reales + recomendaciones · ⚠️ faltan capturas nuevas |
| Autoevaluación contra la rúbrica | ≈51,5 / 53 hoy (ver §8); 53 / 53 con las capturas y la entrega |
| Entrega (.zip, commit, defensa) | ⏳ Pendiente (ver §6) |

## 2. Etapa 1 — ETL con Apache Spark

**Datos:** GBIF *Insecta of Costa Rica (INBio)*, con 3 276 500 especímenes, y la capa de Áreas Silvestres
Protegidas del SINAC 2023, con 173 polígonos. El registro oficial 2025 se usa para validar.

**Resultado:** 3 276 325 documentos. Solo se eliminaron los 175 registros sin coordenadas. 2 064 839 registros
(63 %) caen dentro de un ASP y 1 211 486 fuera.

| Paso del enunciado | Qué se hizo |
|---|---|
| Extracción y exploración | Lectura con Spark (TSV sin comillas, según `meta.xml`), tipos, nulos y pseudo-nulos («Desconocido»), duplicados, estadísticas descriptivas, inconsistencias |
| Limpieza | Duplicados, textos, fechas (rangos `inicio/fin`, años imposibles), coordenadas y elevación (rangos de dominio), corrección de coordenadas invertidas |
| Variables derivadas | `estacion`, `piso_altitudinal`, `precision_temporal_dias`, `amplitud_elevacion_m`, `distancia_borde_m` |
| Imputación (métodos distintos) | Elevación: mediana espacial (celda 1 km → 5 km → cantón), con un error de **12 m frente a 513 m** de la mediana global de Spark ML · Etapa de vida: moda por orden · Provincia/cantón: moda espacial · Sexo/protocolo: constante explícita |
| Anomalías (3 algoritmos) | IQR (Spark, todo el conjunto), Isolation Forest (entrenado con una muestra, aplicado a todo con `mapInPandas`), LOF (muestra estratificada de 50 000) y comparación: cantidades, Jaccard, características y gráficos |
| Integración (join) | Join espacial `ST_Contains` con **Apache Sedona** + *left join* por `id`; aserciones de que no se pierde ni duplica ningún registro; validación con el texto de localidad |
| Preparación para Solr | Esquema de `solr/crear_esquema.py`, `ubicacion` en formato `"lat,lon"`, fechas ISO, JSON Lines con gzip en 23 archivos (61 MB) |

**Problemas de los datos encontrados (documentados en el notebook):**
- En SINAC, `codigo` **no es único**: una ASP tiene varios polígonos y hay 2 códigos reutilizados por áreas
  distintas. Además, los códigos cambiaron entre 2023 y 2025. Se creó un `id_poligono` propio.
- La capa de SINAC no tiene tildes. Se restauraron («Reserva Biológica», «Caño Negro», etc.) para que
  coincidan con los valores de la aplicación.
- **En el INBio, el campo de especie incluye morfoespecies** («sp», «sp12», «cf.», «?»). Hoy se corrigió: `especie`
  solo contiene nombres binomiales válidos (1 040 647 registros). Antes había 1 276 460 y el ranking de la consulta 10
  mostraba «*Lechriops sp*» como especie.

## 3. Integración con el trabajo de Fabián

Él subió 3 commits (consultas convencionales, geoespaciales y documentación LaTeX). Se trajeron a `main` local con
*fast-forward* y mis cambios se aplicaron encima.

- **Revisión del código:** correcto. Valida los campos contra listas permitidas, escapa comillas, usa `geofilt` +
  `geodist()` para proximidad, `Intersects(POLYGON)` con el orden *lon lat* para los polígonos y la JSON Facet API
  para los facets anidados y las estadísticas. Los valores que usa (pisos, «Seca»/«Lluviosa», `dentro_asp`)
  coinciden con los que produce el ETL.
- **Conflicto:** solo en `README.md` (los dos editamos la sección «Estructura»). Se combinaron ambas versiones.
- **Detalle menor:** `quitaComillas()` en `convencionales.py` no se usa. Se dejó tal cual.
- **⚠️ Línea pegada por accidente:** durante la sesión apareció en `backend/app/consultas/convencionales.py`
  (línea 17) el texto `ayer a las 16:59martes, 24 de noviembre de 2026, 16:59`. Rompía todo el backend con un
  `SyntaxError`, así que se eliminó **solo esa línea**. Si era intencional, revisen.

## 4. Resultados con los datos reales

| # | Consulta | Resultado | Tiempo en Solr |
|---|---|---|---|
| 1 | Texto «Morpho» / área «Volcán Poás» | 354 / 1 057 | 1 ms |
| 2 | AND/OR/NOT | 280 284 | 1 ms |
| 3 | Rangos de elevación y fecha | 349 138 | 1 ms |
| 4 | Filtros + orden | 95 997 | <1 ms |
| 5 | Field facet por orden | Coleoptera 895 502, Lepidoptera 618 979… | 55 ms |
| 6 | Range facet por elevación | [0, 250): 1 267 269… | 149 ms |
| 7 | Query facets | Basal 1 626 505; dentro de ASP 2 064 839… | 2 ms |
| 8 | Facets anidados | ACG 545 831, ACOSA 341 302… | 92 ms |
| 9 | Facets con estadísticas | Guanacaste: 309 464, promedio 780 m, 6 918 especies | 186 ms |
| 10 | Ranking de especies (Corcovado) | *Onthophagus acuminatus* 2 462… | 13 ms |
| 11 | Proximidad (San José, 15 km) | 27 720 (1 952 Lepidoptera) | 4 ms |
| 12 | Polígono (península de Osa) | 306 653 | 1 ms |
| 13 | Polígono + facets | Coleoptera 89 485, Lepidoptera 59 610… | 3 ms |

Además: la URL que muestra la aplicación, abierta directamente en Solr, da el mismo total; un polígono con lados
cruzados se repara y responde; y el índice conserva los 3 276 325 documentos tras reiniciar el contenedor. El
frontend compila sin errores.

## 5. Archivos

**Nuevos**
- `etl/etl_insectos.ipynb`: notebook de la Etapa 1, **ya ejecutado** con todas las salidas
- `etl/descargar_datos.py`: descarga los datos crudos (verifica TLS del SINAC sin desactivarlo)
- `etl/Dockerfile`, `etl/requirements.txt`: Jupyter + PySpark 3.5.9 + Sedona 1.9.1 (Java 17)
- `datos/limpios/`: 23 archivos `.json.gz`, `README.md` y `resumen_etl.json`
- `RESUMEN.md`: este archivo

**Modificados**
- `docker-compose.yml`: servicio `spark` (perfil `etl`, no arranca con `docker compose up`)
- `solr/indexar.py`: acepta la carpeta de Spark y archivos `.gz`
- `README.md`: instrucciones de la Etapa 1 y origen de cada campo
- `docs/latex/aplicacion.tex` y `.pdf`: cifras de los datos reales, indexación desde el ETL y notas sobre especies
- `.gitignore`: ignora `datos/crudos/` (≈2,4 GB) y `datos/trabajo/` (Parquet intermedios)

## 6. Pendiente (lo tienen que hacer ustedes)

1. **Revisar y aprobar** las decisiones que tomé sin consulta previa:
   - Umbral de Isolation Forest en el percentil 95. Con el umbral teórico marcaba el 25,8 %.
   - `area_protegida_km2` = área total del ASP (suma de sus partes terrestre, marina e isla).
   - `area_conservacion` en siglas (ACG, ACOSA…).
   - `especie` solo con nombres binomiales válidos (sin morfoespecies).
   - La distancia al borde y las banderas de anomalía quedan solo en el notebook (no van a Solr).
2. **Volver a tomar las 6 capturas** de `docs/img/`, que muestran los datos de muestra: consultas 2 (formulario y
   panel de Solr), 8, 9, 11 y 13. Con la aplicación levantada, ejecutar cada consulta con sus valores por defecto,
   capturar con el mismo nombre de archivo y recompilar con `cd docs/latex && latexmk -pdf aplicacion.tex`.
3. **Commit y push** cuando lo hayan revisado (los temporales de LaTeX ya están ignorados).
4. **El .zip de entrega:** notebook ejecutado + URL del repositorio + datos limpios.
5. **Preparar la defensa** (50 % de cada rubro): poder explicar el ETL, el join espacial y cada consulta.

## 7. Cómo reproducir todo

```bash
# Etapa 1
python3 etl/descargar_datos.py
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose --profile etl build spark
docker compose stop solr        # Spark y Solr juntos no caben en 14 GB de RAM
docker compose --profile etl run --rm spark \
  jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 etl/etl_insectos.ipynb  # ≈7 min

# Etapa 2
docker compose up -d solr
python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/python solr/crear_esquema.py
backend/.venv/bin/python solr/indexar.py datos/limpios/insectos_asp --borrar --lote 10000   # ≈3 min
backend/.venv/bin/pytest backend/tests -q                                                  # 22 passed
backend/.venv/bin/uvicorn app.main:app --app-dir backend --port 8000
npm --prefix frontend install && npm --prefix frontend run dev                             # http://localhost:5173
```

Solr queda levantado ahora mismo con los datos reales indexados (`http://localhost:8983`).

## 8. Autoevaluación contra la rúbrica (sin la columna de defensa)

Se revisó todo el proyecto como lo haría la profesora. La primera revisión dio ≈49,5 / 53. Después se corrigió:

- **Anomalías:** la comparación de los tres algoritmos (conteos, Jaccard, combinaciones, características) pasó de
  pandas a **agregaciones de Spark**, por la regla 7 del enunciado. Solo LOF e Isolation Forest usan scikit-learn,
  porque MLlib no los tiene; está justificado en el notebook.
- **Notebook:** se agregó la interpretación de los 4 gráficos que no la tenían (pisos altitudinales y etapa de vida,
  LOF, comparación de algoritmos, ASP con más registros y mapa) y los nombres de los integrantes.
- **Documento de la aplicación:** se agregó la sección **Recomendaciones**, que pide el enunciado y no estaba.

| Rubro | Puntos | Nota |
|---|---|---|
| Etapa 1 (6 rubros) | 22 | 22 |
| Etapa 2 (6 rubros) | 22 | 22 |
| Documentación del ETL | 3 | 3 |
| Documentación de la aplicación | 3 | 2,5 (las capturas muestran datos sintéticos) |
| Organización y entrega | 3 | 2 (falta el push y el .zip) |
| **Total** | **53** | **≈51,5** |
