#!/usr/bin/env python3
"""
ampliar_corpus.py
=================
Amplía corpus_inventario.csv con cientos de documentos públicos más, para que el corpus
tenga una escala que no quepa en ninguna herramienta de uso general.

Solo AÑADE filas al final: los documentos existentes conservan su id y su nombre.

Fuentes (todas de acceso público):
  capa 3 · Legislación sanitaria española consolidada (API de datos abiertos del BOE)
  capa 3 · Más legislación farmacéutica y sanitaria de la UE (EUR-Lex)
  capa 3 · Publicaciones de la OMS en inglés (repositorio IRIS)
  capa 5 · Artículos científicos con licencia CC BY de PLOS (API de PLOS)
  capa 5 · Artículos científicos con licencia CC BY de Frontiers (vía Europe PMC)

Uso:
    python herramientas/ampliar_corpus.py --dry-run          # solo cuenta
    python herramientas/ampliar_corpus.py                    # añade al CSV
    python descargar_corpus.py --skip-existing               # descarga lo nuevo
    python herramientas/ampliar_corpus.py --podar            # quita del CSV lo que falló
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote

try:
    import requests
except ImportError:
    sys.exit("ERROR: pip install requests")

INVENTARIO = Path("corpus_inventario.csv")
RESULTADOS = Path("nexora_salud_corpus/corpus_resultados.csv")
CAMPOS = ["id", "filename", "titulo", "capa", "categoria", "fuente", "tipo_descarga", "urls"]
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Accept": "application/json"}
MAX_BYTES = 25 * 1024 * 1024       # nada por encima de 25 MB en el repositorio

# Cuántos documentos pedir a cada fuente
CUPOS = {"boe": 60, "eurlex": 14, "oms": 110, "plos": 330, "frontiers": 360}

# ───────────────────────────────────────────────────────────────── utilidades

def slug(texto: str, n: int = 60) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Za-z0-9]+", "_", t).strip("_")
    return t[:n].rstrip("_") or "documento"


def get_json(url: str, **kw):
    # La OMS rechaza la cabecera Accept con un User-Agent de navegador completo
    cab = {"User-Agent": "Mozilla/5.0 (Macintosh) Chrome/120"} if "who.int" in url else UA
    for intento in range(3):
        try:
            r = requests.get(url, headers=cab, timeout=60, **kw)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            if intento == 2:
                print(f"  ⚠ {url[:90]} → {e}")
                return None
            time.sleep(2)


# ───────────────────────────────────────────────────────────────── fuentes

def fuente_boe(cupo):
    """Leyes y reales decretos estatales consolidados con contenido sanitario."""
    terminos = ["sanidad", "sanitari*", "salud", "medicamento*", "paciente*", "farmac*",
                "hospital*", "enfermer*", "vacun*", "donaci*", "trasplant*", "biomedic*"]
    rangos_ok = {"Ley", "Ley Orgánica", "Real Decreto", "Real Decreto-ley",
                 "Real Decreto Legislativo"}
    vistos, filas = set(), []
    for term in terminos:
        q = '{"query":{"query_string":{"query":"titulo:%s"}}}' % term
        d = get_json("https://www.boe.es/datosabiertos/api/legislacion-consolidada",
                     params={"query": q, "limit": 200})
        for it in (d or {}).get("data", []):
            ident = it.get("identificador", "")
            if ident in vistos or it.get("rango", {}).get("texto") not in rangos_ok:
                continue
            if it.get("ambito", {}).get("texto") != "Estatal":
                continue
            if it.get("vigencia_agotada") == "S" or it.get("estatus_derogacion") == "S":
                continue
            vistos.add(ident)
            anio = ident.split("-")[2]
            titulo = re.sub(r"\s+", " ", it.get("titulo", ident))
            filas.append(dict(fichero=f"BOE_{ident}_{slug(titulo, 50)}.pdf", titulo=titulo,
                              capa=3, categoria="Regulacion_ES", fuente="BOE",
                              url=f"https://www.boe.es/buscar/pdf/{anio}/{ident}-consolidado.pdf"))
        if len(filas) >= cupo:
            break
    return filas[:cupo]


EURLEX_EXTRA = [
    ("32001L0083", "Directiva 2001/83/CE — Código comunitario de medicamentos de uso humano"),
    ("32004R0726", "Reglamento (CE) 726/2004 — Procedimientos de autorización y Agencia Europea de Medicamentos"),
    ("32022R2371", "Reglamento (UE) 2022/2371 — Amenazas transfronterizas graves para la salud"),
    ("32022R0123", "Reglamento (UE) 2022/123 — Refuerzo del papel de la Agencia Europea de Medicamentos"),
    ("32006R1901", "Reglamento (CE) 1901/2006 — Medicamentos para uso pediátrico"),
    ("32000R0141", "Reglamento (CE) 141/2000 — Medicamentos huérfanos"),
    ("32007R1394", "Reglamento (CE) 1394/2007 — Medicamentos de terapia avanzada"),
    ("32024R1938", "Reglamento (UE) 2024/1938 — Sustancias de origen humano"),
    ("32010L0084", "Directiva 2010/84/UE — Farmacovigilancia"),
    ("32011L0062", "Directiva 2011/62/UE — Medicamentos falsificados"),
    ("32021R0522", "Reglamento (UE) 2021/522 — Programa UEproSalud (EU4Health)"),
    ("32002L0098", "Directiva 2002/98/CE — Calidad y seguridad de la sangre humana"),
    ("32004L0023", "Directiva 2004/23/CE — Calidad y seguridad de tejidos y células humanos"),
    ("32022R0868", "Reglamento (UE) 2022/868 — Gobernanza Europea de Datos"),
]


def fuente_eurlex(cupo):
    return [dict(fichero=f"EURLEX_{celex}_{slug(t, 50)}.pdf", titulo=t, capa=3,
                 categoria="Regulacion_UE", fuente="EUR-Lex",
                 url=f"https://eur-lex.europa.eu/legal-content/ES/TXT/PDF/?uri=CELEX:{celex}")
            for celex, t in EURLEX_EXTRA[:cupo]]


def fuente_oms(cupo):
    """Publicaciones de la OMS en inglés sobre IA, salud digital, diabetes y guías."""
    consultas = ["artificial intelligence health", "digital health", "diabetes guidelines",
                 "WHO guidelines", "health data governance", "patient safety",
                 "noncommunicable diseases", "primary health care", "mental health guidance",
                 "health technology assessment", "telemedicine"]
    vistos, filas = set(), []
    base = "https://iris.who.int/server/api"
    for q in consultas:
        for page in range(3):
            d = get_json(f"{base}/discover/search/objects",
                         params={"query": q, "dsoType": "ITEM", "size": 20, "page": page})
            objs = (((d or {}).get("_embedded") or {}).get("searchResult") or {}) \
                .get("_embedded", {}).get("objects", [])
            if not objs:
                break
            for o in objs:
                item = o["_embedded"]["indexableObject"]
                if item["uuid"] in vistos:
                    continue
                vistos.add(item["uuid"])
                bund = get_json(f"{base}/core/items/{item['uuid']}/bundles")
                for b in ((bund or {}).get("_embedded") or {}).get("bundles", []):
                    if b.get("name") != "ORIGINAL":
                        continue
                    bits = get_json(b["_links"]["bitstreams"]["href"])
                    for bs in ((bits or {}).get("_embedded") or {}).get("bitstreams", []):
                        nombre = bs.get("name", "")
                        if not nombre.lower().endswith("-eng.pdf"):
                            continue
                        if not 50_000 < (bs.get("sizeBytes") or 0) <= MAX_BYTES:
                            continue
                        titulo = re.sub(r"\s+", " ", item.get("name", nombre))
                        filas.append(dict(fichero=f"OMS_{slug(titulo, 60)}.pdf",
                                          titulo=f"OMS — {titulo}", capa=3,
                                          categoria="Orientaciones_OMS", fuente="OMS",
                                          url=f"{base}/core/bitstreams/{bs['uuid']}/content"))
                        break
                if len(filas) >= cupo:
                    return filas
    return filas


def fuente_plos(cupo):
    """Artículos de PLOS (CC BY) sobre IA y datos en salud, y sobre diabetes."""
    consultas = [
        'abstract:("artificial intelligence" OR "machine learning" OR "deep learning") AND abstract:(clinical OR hospital OR patient)',
        'abstract:("large language model" OR "ChatGPT" OR "natural language processing") AND abstract:(health OR medical)',
        'abstract:("clinical decision support" OR "electronic health record")',
        'title:diabetes AND abstract:("machine learning" OR "prediction model" OR "guideline")',
    ]
    vistos, filas = set(), []
    por_consulta = cupo // len(consultas) + 1
    for q in consultas:
        d = get_json("https://api.plos.org/search",
                     params={"q": q, "fq": "doc_type:full",
                             "fl": "id,title_display,journal,publication_date",
                             "rows": por_consulta * 2, "sort": "publication_date desc"})
        n = 0
        for doc in (d or {}).get("response", {}).get("docs", []):
            doi = doc["id"]
            if doi in vistos or "/annotation/" in doi:
                continue
            vistos.add(doi)
            titulo = re.sub(r"<[^>]+>|\s+", " ", doc.get("title_display", doi)).strip()
            revista = doc.get("journal", "PLOS")
            codigo = doi.split("journal.")[-1]
            filas.append(dict(fichero=f"PLOS_{codigo}_{slug(titulo, 45)}.pdf",
                              titulo=f"{titulo} ({revista}, {doc.get('publication_date', '')[:4]})",
                              capa=5, categoria="Literatura_IA_salud", fuente="PLOS (CC BY)",
                              url=f"https://journals.plos.org/plosone/article/file?id={doi}&type=printable"))
            n += 1
            if n >= por_consulta:
                break
    return filas[:cupo]


def fuente_frontiers(cupo):
    """Artículos de Frontiers (CC BY) localizados con Europe PMC."""
    consultas = [
        '("artificial intelligence" OR "machine learning") AND (clinical OR hospital)',
        '("large language model" OR "ChatGPT" OR "retrieval-augmented")',
        '(diabetes) AND ("machine learning" OR "artificial intelligence" OR "digital health")',
        '("clinical decision support" OR "digital health" OR "telemedicine")',
    ]
    vistos, filas = set(), []
    por_consulta = cupo // len(consultas) + 1
    for q in consultas:
        query = f'{q} AND PUBLISHER:"Frontiers Media SA" AND OPEN_ACCESS:y AND PUB_YEAR:[2022 TO 2026]'
        cursor, n = "*", 0
        while n < por_consulta and cursor:
            d = get_json("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                         params={"query": query, "format": "json", "pageSize": 100,
                                 "cursorMark": cursor, "sort": "P_PDATE_D desc"})
            if not d:
                break
            for r in d.get("resultList", {}).get("result", []):
                doi = r.get("doi")
                if not doi or not doi.startswith("10.3389/") or doi in vistos:
                    continue
                if (r.get("pubType") or "").lower().find("correction") >= 0 \
                        or r.get("title", "").lower().startswith(("correction", "erratum", "editorial")):
                    continue
                vistos.add(doi)
                titulo = re.sub(r"<[^>]+>|\s+", " ", r.get("title", doi)).strip().rstrip(".")
                filas.append(dict(fichero=f"FRONTIERS_{slug(doi.split('/')[-1], 30)}_{slug(titulo, 40)}.pdf",
                                  titulo=f"{titulo} ({r.get('journalTitle', 'Frontiers')}, {r.get('pubYear', '')})",
                                  capa=5, categoria="Literatura_IA_salud", fuente="Frontiers (CC BY)",
                                  url=f"https://www.frontiersin.org/articles/{doi}/pdf"))
                n += 1
                if n >= por_consulta:
                    break
            nuevo = d.get("nextCursorMark")
            cursor = None if nuevo == cursor else nuevo
    return filas[:cupo]


# ───────────────────────────────────────────────────────────────── main

def leer():
    with open(INVENTARIO, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def escribir(filas):
    with open(INVENTARIO, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=";")
        w.writeheader()
        w.writerows(filas)


def podar():
    """Quita del inventario las filas cuya descarga falló, y borra PDF demasiado grandes."""
    estado = {}
    with open(RESULTADOS, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            estado[r["filename"]] = r.get("estado", "")
    filas, quitadas = [], 0
    for r in leer():
        pdf = RESULTADOS.parent / r["filename"]
        grande = pdf.exists() and pdf.stat().st_size > MAX_BYTES
        if grande:
            pdf.unlink()
        if estado.get(r["filename"]) in ("OK", "SKIP") and not grande:
            filas.append(r)
        else:
            quitadas += 1
    escribir(filas)
    print(f"Podadas {quitadas} filas. Quedan {len(filas)} documentos.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--podar", action="store_true")
    args = ap.parse_args()
    if args.podar:
        return podar()

    actuales = leer()
    urls = {r["urls"] for r in actuales}
    nid = max(int(r["id"]) for r in actuales)
    nuevas = []
    for nombre, fn in (("boe", fuente_boe), ("eurlex", fuente_eurlex), ("oms", fuente_oms),
                       ("plos", fuente_plos), ("frontiers", fuente_frontiers)):
        filas = [f for f in fn(CUPOS[nombre]) if f["url"] not in urls]
        print(f"{nombre:10s} {len(filas):4d} documentos")
        for f in filas:
            urls.add(f["url"])
            nid += 1
            nuevas.append({"id": f"{nid:03d}", "filename": f"{nid:03d}_{f['fichero']}",
                           "titulo": f["titulo"], "capa": f["capa"], "categoria": f["categoria"],
                           "fuente": f["fuente"], "tipo_descarga": "web", "urls": f["url"]})
    print(f"Total nuevos: {len(nuevas)} · el inventario pasaría de {len(actuales)} a {len(actuales) + len(nuevas)}")
    if not args.dry_run:
        escribir(actuales + nuevas)
        print(f"→ {INVENTARIO} actualizado")


if __name__ == "__main__":
    main()
