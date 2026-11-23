"""Genera un dataset de MUESTRA con el esquema que se indexará en Solr.

Mientras la Etapa 1 (Spark) no entregue el dataset real, este script produce
documentos sintéticos con los mismos campos que tendrá el archivo final:
ocurrencias de insectos (estilo GBIF / INBio) unidas con el área silvestre
protegida (estilo SINAC) donde se registraron.

Los datos NO son reales: las áreas protegidas, sus categorías y su área de
conservación sí existen, pero las coordenadas son aproximadas (se generan
alrededor de un centroide) y las ocurrencias son aleatorias. Sirven para
desarrollar y probar la aplicación; se reemplazan por el archivo de Spark.

Uso:
    python datos/generar_muestra.py                    # 100 000 docs
    python datos/generar_muestra.py --n 20000 --salida datos/muestra/chica.jsonl

Es reproducible: la misma --semilla produce exactamente los mismos documentos.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Áreas silvestres protegidas (SINAC). Centroides y extensiones aproximados.
# (nombre, categoría de manejo, área de conservación, km², lat, lon,
#  provincia, cantón, elevación media m, desviación de la elevación m)
# ---------------------------------------------------------------------------
AREAS = [
    ("Corcovado", "Parque Nacional", "ACOSA", 424, 8.54, -83.58, "Puntarenas", "Osa", 250, 200),
    ("Braulio Carrillo", "Parque Nacional", "ACC", 475, 10.15, -83.95, "Heredia", "Sarapiquí", 1200, 700),
    ("Tortuguero", "Parque Nacional", "ACTo", 312, 10.50, -83.55, "Limón", "Pococí", 40, 30),
    ("Santa Rosa", "Parque Nacional", "ACG", 387, 10.85, -85.62, "Guanacaste", "La Cruz", 250, 150),
    ("Rincón de la Vieja", "Parque Nacional", "ACG", 141, 10.80, -85.35, "Guanacaste", "Liberia", 1000, 400),
    ("Guanacaste", "Parque Nacional", "ACG", 340, 10.95, -85.48, "Guanacaste", "La Cruz", 600, 350),
    ("Chirripó", "Parque Nacional", "ACLA-P", 502, 9.47, -83.50, "San José", "Pérez Zeledón", 2600, 500),
    ("Volcán Arenal", "Parque Nacional", "ACAHN", 121, 10.46, -84.72, "Alajuela", "San Carlos", 700, 250),
    ("Manuel Antonio", "Parque Nacional", "ACOPAC", 20, 9.38, -84.14, "Puntarenas", "Quepos", 60, 50),
    ("Cahuita", "Parque Nacional", "ACLA-C", 11, 9.73, -82.83, "Limón", "Talamanca", 10, 10),
    ("Tapantí-Macizo de la Muerte", "Parque Nacional", "ACC", 583, 9.70, -83.78, "Cartago", "Paraíso", 1800, 600),
    ("Carara", "Parque Nacional", "ACOPAC", 52, 9.78, -84.60, "Puntarenas", "Garabito", 200, 150),
    ("Palo Verde", "Parque Nacional", "ACAT", 184, 10.35, -85.33, "Guanacaste", "Bagaces", 40, 30),
    ("Piedras Blancas", "Parque Nacional", "ACOSA", 140, 8.69, -83.24, "Puntarenas", "Golfito", 200, 150),
    ("La Amistad", "Parque Nacional", "ACLA-P", 1990, 9.15, -82.95, "Puntarenas", "Buenos Aires", 1900, 700),
    ("Barra Honda", "Parque Nacional", "ACT", 23, 10.18, -85.36, "Guanacaste", "Nicoya", 300, 120),
    ("Volcán Poás", "Parque Nacional", "ACC", 65, 10.20, -84.23, "Alajuela", "Grecia", 2400, 250),
    ("Volcán Irazú", "Parque Nacional", "ACC", 20, 9.98, -83.85, "Cartago", "Oreamuno", 3000, 200),
    ("Hitoy Cerere", "Reserva Biológica", "ACLA-C", 99, 9.67, -83.03, "Limón", "Talamanca", 500, 300),
    ("Lomas de Barbudal", "Reserva Biológica", "ACAT", 26, 10.48, -85.38, "Guanacaste", "Bagaces", 150, 80),
    ("Alberto Manuel Brenes", "Reserva Biológica", "ACCVC", 78, 10.22, -84.60, "Alajuela", "San Ramón", 900, 200),
    ("Isla del Caño", "Reserva Biológica", "ACOSA", 3, 8.71, -83.88, "Puntarenas", "Osa", 40, 30),
    ("Caño Negro", "Refugio Nacional de Vida Silvestre", "ACAHN", 99, 10.90, -84.78, "Alajuela", "Los Chiles", 40, 20),
    ("Gandoca-Manzanillo", "Refugio Nacional de Vida Silvestre", "ACLA-C", 50, 9.62, -82.65, "Limón", "Talamanca", 20, 20),
    ("Ostional", "Refugio Nacional de Vida Silvestre", "ACT", 4, 9.99, -85.70, "Guanacaste", "Santa Cruz", 15, 10),
    ("El Rodeo", "Zona Protectora", "ACC", 25, 9.91, -84.27, "San José", "Mora", 900, 150),
    ("Los Santos", "Reserva Forestal", "ACLA-P", 620, 9.60, -83.80, "San José", "Dota", 2300, 450),
    ("Térraba-Sierpe", "Humedal", "ACOSA", 270, 8.85, -83.55, "Puntarenas", "Osa", 10, 10),
    ("Guayabo", "Monumento Nacional", "ACC", 2, 9.97, -83.69, "Cartago", "Turrialba", 1100, 60),
    ("Cabo Blanco", "Reserva Natural Absoluta", "ACT", 13, 9.57, -85.11, "Puntarenas", "Puntarenas", 200, 120),
]

# Lugares fuera de áreas protegidas (para los registros sin correspondencia
# del join): (cantón, provincia, lat, lon, elevación media, desviación)
FUERA_ASP = [
    ("San José", "San José", 9.93, -84.08, 1150, 100),
    ("Liberia", "Guanacaste", 10.63, -85.44, 150, 60),
    ("Limón", "Limón", 9.99, -83.03, 30, 20),
    ("Pérez Zeledón", "San José", 9.37, -83.70, 700, 200),
    ("San Carlos", "Alajuela", 10.32, -84.43, 400, 200),
    ("Puntarenas", "Puntarenas", 9.98, -84.83, 20, 15),
    ("Nicoya", "Guanacaste", 10.15, -85.45, 150, 80),
    ("Turrialba", "Cartago", 9.90, -83.68, 650, 150),
]

# ---------------------------------------------------------------------------
# Taxonomía: orden -> peso, familias -> [(género, epíteto o None)]
# Géneros y especies reales presentes en Costa Rica.
# ---------------------------------------------------------------------------
TAXONOMIA = {
    "Lepidoptera": (30, {
        "Nymphalidae": [("Morpho", "peleides"), ("Heliconius", "erato"), ("Caligo", "memnon"), ("Siproeta", "stelenes")],
        "Papilionidae": [("Papilio", "thoas"), ("Parides", "iphidamas")],
        "Sphingidae": [("Manduca", "sexta"), ("Xylophanes", "tersa")],
        "Saturniidae": [("Rothschildia", "lebeau"), ("Automeris", "zugana")],
        "Erebidae": [("Ascalapha", "odorata")],
    }),
    "Coleoptera": (25, {
        "Scarabaeidae": [("Phanaeus", "demon"), ("Dynastes", "hercules"), ("Chrysina", "resplendens")],
        "Cerambycidae": [("Acrocinus", "longimanus")],
        "Curculionidae": [("Rhynchophorus", "palmarum")],
        "Carabidae": [("Calosoma", "sayi")],
        "Chrysomelidae": [("Diabrotica", "balteata")],
    }),
    "Hymenoptera": (18, {
        "Formicidae": [("Atta", "cephalotes"), ("Eciton", "burchellii"), ("Paraponera", "clavata")],
        "Apidae": [("Euglossa", "imperialis"), ("Melipona", "beecheii"), ("Trigona", "fulviventris")],
        "Vespidae": [("Polybia", "occidentalis")],
    }),
    "Diptera": (12, {
        "Syrphidae": [("Ornidia", "obesa")],
        "Tephritidae": [("Anastrepha", "ludens")],
        "Ulidiidae": [("Euxesta", None)],
        "Culicidae": [("Aedes", "aegypti")],
    }),
    "Hemiptera": (7, {
        "Fulgoridae": [("Fulgora", "laternaria")],
        "Cicadidae": [("Fidicina", "mannifera")],
        "Pentatomidae": [("Edessa", "rufomarginata")],
        "Reduviidae": [("Triatoma", "dimidiata")],
    }),
    "Orthoptera": (3, {
        "Tettigoniidae": [("Pterochroza", "ocellata")],
        "Romaleidae": [("Taeniopoda", "reticulata")],
    }),
    "Odonata": (2, {
        "Libellulidae": [("Erythrodiplax", "umbrata")],
        "Pseudostigmatidae": [("Megaloprepus", "caerulatus")],
    }),
    "Blattodea": (1.5, {"Blaberidae": [("Blaberus", "giganteus")]}),
    "Mantodea": (1.5, {"Mantidae": [("Stagmomantis", "theophila")]}),
}

ETAPAS = (["Adulto", "Larva", "Pupa", "Ninfa"], [85, 10, 3, 2])
SEXOS = (["Indeterminado", "Macho", "Hembra"], [50, 25, 25])
PROTOCOLOS = (["Trampa de luz", "Manual", "Trampa Malaise", "Trampa de caída", "Red entomológica"], [35, 25, 15, 10, 15])
RECOLECTORES = [f"Parataxónomo {i:02d}" for i in range(1, 41)]
SECTORES = ["Estación Biológica", "Sendero principal", "Sector norte", "Sector sur", "Puesto de guardaparques", "Quebrada"]

FECHA_INICIO = date(1985, 1, 1)
FECHA_FIN = date(2015, 12, 31)


def piso_altitudinal(elev: float) -> str:
    """Variable derivada: franja altitudinal simplificada."""
    if elev < 500:
        return "Basal"
    if elev < 1500:
        return "Premontano"
    if elev < 2500:
        return "Montano bajo"
    return "Montano"


def estacion(mes: int) -> str:
    """Variable derivada: estación seca (dic–abr) o lluviosa (may–nov)."""
    return "Seca" if mes in (12, 1, 2, 3, 4) else "Lluviosa"


def punto_alrededor(rng: random.Random, lat: float, lon: float, km2: float) -> tuple[float, float]:
    radio_km = math.sqrt(km2 / math.pi)
    sigma = max(radio_km * 0.5, 0.3) / 111.0
    la = rng.gauss(lat, sigma)
    lo = rng.gauss(lon, sigma / math.cos(math.radians(lat)))
    # Límites aproximados del territorio continental de Costa Rica
    la = min(max(la, 8.0), 11.2)
    lo = min(max(lo, -85.95), -82.55)
    return round(la, 6), round(lo, 6)


def fecha_aleatoria(rng: random.Random) -> date:
    # Más colectas entre 1990 y 2008 (época de mayor actividad de INBio)
    anio = int(min(max(rng.gauss(1999, 6), FECHA_INICIO.year), FECHA_FIN.year))
    inicio = date(anio, 1, 1)
    return inicio + timedelta(days=rng.randrange(365))


def elegir_taxon(rng: random.Random) -> dict:
    ordenes = list(TAXONOMIA)
    orden = rng.choices(ordenes, weights=[TAXONOMIA[o][0] for o in ordenes])[0]
    familias = TAXONOMIA[orden][1]
    familia = rng.choice(list(familias))
    genero, epiteto = rng.choice(familias[familia])
    # Como en INBio, no todo está identificado hasta especie
    r = rng.random()
    if r < 0.6 and epiteto:
        rango, nombre, especie = "ESPECIE", f"{genero} {epiteto}", f"{genero} {epiteto}"
    elif r < 0.8:
        rango, nombre, especie = "GENERO", genero, None
    else:
        rango, nombre, especie, genero = "FAMILIA", familia, None, None
    doc = {"orden": orden, "familia": familia, "rango_taxonomico": rango, "nombre_cientifico": nombre}
    if genero:
        doc["genero"] = genero
    if especie:
        doc["especie"] = especie
    return doc


def generar_doc(rng: random.Random, i: int) -> dict:
    doc = {"id": f"M-{i:07d}"}
    doc.update(elegir_taxon(rng))

    if rng.random() < 0.85:
        nombre, cat, ac, km2, lat, lon, prov, canton, emed, esd = rng.choice(AREAS)
        la, lo = punto_alrededor(rng, lat, lon, km2)
        doc.update({
            "dentro_asp": True,
            "area_protegida": nombre,
            "categoria_manejo": cat,
            "area_conservacion": ac,
            "area_protegida_km2": float(km2),
            "localidad": f"{cat} {nombre}, {rng.choice(SECTORES)}",
        })
    else:
        canton, prov, lat, lon, emed, esd = rng.choice(FUERA_ASP)
        la, lo = punto_alrededor(rng, lat, lon, 150)
        doc.update({
            "dentro_asp": False,
            "area_protegida": "Fuera de ASP",
            "categoria_manejo": "Sin categoría",
            "area_conservacion": "Sin área de conservación",
            "localidad": f"{canton}, finca privada",
        })

    elev = max(0.0, round(rng.gauss(emed, esd), 0))
    f = fecha_aleatoria(rng)
    doc.update({
        "provincia": prov,
        "canton": canton,
        "latitud": la,
        "longitud": lo,
        "ubicacion": f"{la},{lo}",  # formato "lat,lon" de Solr
        "elevacion_m": elev,
        "fecha_evento": f"{f.isoformat()}T00:00:00Z",
        "anio": f.year,
        "mes": f.month,
        "etapa_vida": rng.choices(*ETAPAS)[0],
        "sexo": rng.choices(*SEXOS)[0],
        "protocolo_muestreo": rng.choices(*PROTOCOLOS)[0],
        "recolector": rng.choice(RECOLECTORES),
        "piso_altitudinal": piso_altitudinal(elev),
        "estacion": estacion(f.month),
    })
    return doc


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--n", type=int, default=100_000, help="cantidad de documentos")
    p.add_argument("--semilla", type=int, default=2026)
    p.add_argument("--salida", default=str(Path(__file__).parent / "muestra" / "insectos_muestra.jsonl"))
    args = p.parse_args()

    rng = random.Random(args.semilla)
    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("w", encoding="utf-8") as fh:
        for i in range(1, args.n + 1):
            fh.write(json.dumps(generar_doc(rng, i), ensure_ascii=False) + "\n")
    print(f"{args.n} documentos escritos en {salida}")


if __name__ == "__main__":
    main()
