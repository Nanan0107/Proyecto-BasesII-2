# Datos limpios — ocurrencias de insectos integradas con las ASP

Salida final del ETL de la Etapa 1 (`etl/etl_insectos.ipynb`), lista para indexar en Apache Solr.

| | |
|---|---|
| Documentos | 3 276 325 (una ocurrencia = un documento, `id` único) |
| Dentro de un ASP | 2 064 839 (63,0 %) |
| Fuera de ASP | 1 211 486 (`dentro_asp=false`, `area_protegida="Fuera de ASP"`) |
| Formato | JSON Lines comprimido con gzip, 23 archivos `insectos_asp/part-*.json.gz` (≈61 MB, cada uno < 6 MB) |
| Orden | por `id` dentro de cada archivo; los archivos cubren rangos de `id` consecutivos |
| Esquema | el de `solr/crear_esquema.py` (ver tabla del README principal) |
| Resumen | `resumen_etl.json`: conteos y bitácora de registros por paso del ETL |

Los campos sin valor se omiten del documento (en Solr, campo ausente = sin valor). Los nombres de archivo los
genera Spark y cambian en cada corrida; el contenido es determinístico.

## Cómo leerlos

```bash
# Indexar en Solr
backend/.venv/bin/python solr/indexar.py datos/limpios/insectos_asp --borrar
```
```python
# Spark
spark.read.json("datos/limpios/insectos_asp")
# pandas (un archivo)
pd.read_json("datos/limpios/insectos_asp/part-00000-….json.gz", lines=True)
```
```bash
# Línea de comandos
zcat datos/limpios/insectos_asp/part-*.json.gz | head -1
```

## Fuentes

- INBio, *Insecta of Costa Rica (INBio)*, GBIF, dataset `3e9817c1-8302-4955-87e3-a408db0ea379` (CC0 1.0).
- SINAC, *Límites de las Áreas Silvestres Protegidas*, versión 2023.

Para regenerarlos: `python3 etl/descargar_datos.py` y ejecutar el notebook (ver README principal).
