#!/usr/bin/env python3
"""
estadisticas_corpus.py
======================
Cuenta documentos, páginas, caracteres, tokens y trozos del corpus, en total y por capa,
y lo guarda en docs/estadisticas_corpus.json.

    pip install pymupdf
    python herramientas/estadisticas_corpus.py
"""
from __future__ import annotations

import collections
import csv
import json
import os
from pathlib import Path

import pymupdf

CORPUS = Path("nexora_salud_corpus")
INVENTARIO = Path("corpus_inventario.csv")
SALIDA = Path("docs/estadisticas_corpus.json")

CHARS_POR_TOKEN = 4          # aproximación
CHARS_POR_PALABRA = 6        # aproximación para español
CHUNK, SOLAPE = 1000, 200


def main():
    inv = {r["filename"]: r for r in csv.DictReader(open(INVENTARIO, encoding="utf-8"), delimiter=";")}
    tot = collections.Counter()
    capa = collections.defaultdict(collections.Counter)
    fuente = collections.defaultdict(collections.Counter)
    avisos = []
    for nombre, r in inv.items():
        f = CORPUS / nombre
        if not f.exists():
            avisos.append(f"falta {nombre}")
            continue
        try:
            with pymupdf.open(f) as d:
                pags = d.page_count
                chars = sum(len(p.get_text()) for p in d)
        except Exception as e:  # noqa: BLE001
            avisos.append(f"ilegible {nombre}: {e}")
            continue
        if chars < 500:
            avisos.append(f"casi sin texto {nombre} ({chars} caracteres en {pags} págs)")
        for dest in (tot, capa[r["capa"]], fuente[r["fuente"]]):
            dest.update(docs=1, paginas=pags, caracteres=chars, bytes=os.path.getsize(f))
    tot["palabras_aprox"] = tot["caracteres"] // CHARS_POR_PALABRA
    tot["tokens_aprox"] = tot["caracteres"] // CHARS_POR_TOKEN
    tot["trozos_aprox"] = tot["caracteres"] // (CHUNK - SOLAPE)
    res = {"total": dict(tot),
           "por_capa": {k: dict(v) for k, v in sorted(capa.items())},
           "por_fuente": {k: dict(v) for k, v in sorted(fuente.items())},
           "supuestos": {"caracteres_por_token": CHARS_POR_TOKEN,
                         "caracteres_por_palabra": CHARS_POR_PALABRA,
                         "trozo": CHUNK, "solape": SOLAPE},
           "avisos": avisos}
    SALIDA.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    t = res["total"]
    print(f"{t['docs']} documentos · {t['paginas']:,} páginas · {t['caracteres']:,} caracteres · "
          f"~{t['tokens_aprox']:,} tokens · ~{t['trozos_aprox']:,} trozos · {t['bytes'] / 1e9:.2f} GB"
          .replace(",", "."))
    for k, v in res["por_capa"].items():
        print(f"  capa {k}: {v['docs']} docs, {v['paginas']:,} págs".replace(",", "."))
    if avisos:
        print(f"  {len(avisos)} avisos (ver {SALIDA})")


if __name__ == "__main__":
    main()
