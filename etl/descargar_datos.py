"""Descarga los dos conjuntos de datos crudos del proyecto en datos/crudos/.

1. GBIF — «Insecta of Costa Rica (INBio)»
   https://www.gbif.org/dataset/3e9817c1-8302-4955-87e3-a408db0ea379
   Archivo Darwin Core (DwC-A) publicado por GBIF, licencia CC0.
2. SINAC — Límites de las Áreas Silvestres Protegidas (shapefile v2023) y
   registro oficial de ASP (xls, versión 2025).
   https://www.sinac.go.cr/ES/asp/Paginas/default.aspx

Nota TLS: el servidor de SINAC solo envía su propio certificado, sin el
intermedio «Go Daddy Secure Certificate Authority - G2». En lugar de desactivar
la verificación, el script descarga ese intermedio desde la URL que el propio
certificado indica (Authority Information Access) y lo agrega al almacén de
confianza. La cadena se sigue validando hasta la raíz GoDaddy G2 del sistema,
por lo que un intermedio falso sería rechazado.

Uso (solo biblioteca estándar, sirve dentro o fuera del contenedor):
    python etl/descargar_datos.py            # descarga lo que falte
    python etl/descargar_datos.py --forzar   # vuelve a descargar todo
"""

from __future__ import annotations

import argparse
import ssl
import sys
import urllib.request
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CRUDOS = RAIZ / "datos" / "crudos"

GBIF_URL = "https://orphans.gbif.org/CR/3e9817c1-8302-4955-87e3-a408db0ea379.zip"
SINAC_BASE = "https://www.sinac.go.cr/ES/asp/Documents/"
SINAC_SHP = SINAC_BASE + "Areas_Silvestres_Protegidas_v2023.zip"
SINAC_XLS = SINAC_BASE + "%C3%81reas%20Silvestres%20Protegidas%20de%20Costa%20Rica%20versi%C3%B3n%202025.xls"
GODADDY_G2_INTERMEDIO = "http://certificates.godaddy.com/repository/gdig2.crt"


def contexto_sinac() -> ssl.SSLContext:
    """Contexto TLS con las CA del sistema + el intermedio que SINAC omite."""
    with urllib.request.urlopen(GODADDY_G2_INTERMEDIO, timeout=30) as r:
        der = r.read()
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(cadata=ssl.DER_cert_to_PEM_cert(der))
    return ctx


def descargar(url: str, destino: Path, ctx: ssl.SSLContext | None = None, forzar: bool = False) -> None:
    if destino.exists() and not forzar:
        print(f"  ya existe {destino.relative_to(RAIZ)} ({destino.stat().st_size / 1e6:.1f} MB)")
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(destino.suffix + ".part")
    with urllib.request.urlopen(url, timeout=120, context=ctx) as r, tmp.open("wb") as fh:
        total = int(r.headers.get("Content-Length", 0))
        leidos = 0
        while bloque := r.read(1 << 20):
            fh.write(bloque)
            leidos += len(bloque)
            if total:
                print(f"\r  {destino.name}: {leidos / 1e6:.1f}/{total / 1e6:.1f} MB", end="", flush=True)
    tmp.rename(destino)
    print(f"\r  descargado {destino.relative_to(RAIZ)} ({leidos / 1e6:.1f} MB)        ")


def extraer(zip_path: Path, destino: Path) -> None:
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(destino)
        print(f"  extraído en {destino.relative_to(RAIZ)}: {', '.join(sorted(z.namelist()))}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--forzar", action="store_true", help="descargar aunque el archivo exista")
    args = p.parse_args()

    print("GBIF — Insecta of Costa Rica (INBio)")
    gbif_zip = CRUDOS / "gbif" / "insecta_inbio_dwca.zip"
    descargar(GBIF_URL, gbif_zip, forzar=args.forzar)
    extraer(gbif_zip, CRUDOS / "gbif" / "dwca")

    print("SINAC — Áreas Silvestres Protegidas")
    try:
        ctx = contexto_sinac()
    except OSError as e:
        sys.exit(f"No se pudo obtener el certificado intermedio de GoDaddy: {e}")
    shp_zip = CRUDOS / "sinac" / "Areas_Silvestres_Protegidas_v2023.zip"
    descargar(SINAC_SHP, shp_zip, ctx, args.forzar)
    extraer(shp_zip, CRUDOS / "sinac" / "asp_v2023")
    descargar(SINAC_XLS, CRUDOS / "sinac" / "registro_asp_2025.xls", ctx, args.forzar)

    print("Listo.")


if __name__ == "__main__":
    main()
