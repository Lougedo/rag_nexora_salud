#!/usr/bin/env python3
"""
descargar_corpus.py
====================
Script genérico para descargar un corpus de PDFs a partir de un CSV de
inventario con URLs alternativas.

Diseñado originalmente para el corpus NEXORA Salud (guías clínicas y normativa sanitaria), pero
cualquier otro corpus funciona con tal de que el CSV respete el mismo
formato (ver CSV_SCHEMA más abajo).

Uso:
    python descargar_corpus.py
    python descargar_corpus.py --inventario corpus_inventario.csv
    python descargar_corpus.py --output-dir ./mi_corpus --skip-existing
    python descargar_corpus.py --local-docs-dir ~/Desktop/nexora_salud_interno
    python descargar_corpus.py --only-capa 1,2
    python descargar_corpus.py --only-ids 28,54,55,61
    python descargar_corpus.py --only-categoria Endocrinologia,Regulacion_UE

Requisitos:
    pip install requests

CSV_SCHEMA
----------
Separador de campos: ';'
Separador de URLs alternativas dentro del campo 'urls': '|'

Columnas obligatorias:
    id              - identificador corto (ej. '28')
    filename        - nombre del PDF destino
    titulo          - título humano del documento
    capa            - 1=guías clínicas, 2=complementario, 3=normativa, 4=interno
    categoria       - etiqueta temática (ej. 'Endocrinologia', 'Regulacion_UE',
                      'Estrategia_ES', 'Interno_NEXORA', ...). Permite filtrar
                      y agrupar sin cambiar la capa.
    fuente          - organismo emisor (GuiaSalud, EUR-Lex, BOE, OMS, FDA, NEXORA Salud, ...)
    tipo_descarga   - 'web' (descarga HTTP) o 'local' (copia desde disco)
    urls            - una o más URLs/rutas separadas por '|'
                      para tipo_descarga=web: URLs con fallback en orden
                      para tipo_descarga=local: nombre del fichero a copiar
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
import time
from pathlib import Path
from typing import List, Tuple

try:
    import requests
except ImportError:
    print("ERROR: pip install requests")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,application/octet-stream,*/*",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}

CAPA_NAMES = {
    "1": "Guías de práctica clínica del SNS",
    "2": "Material complementario de las guías",
    "3": "Normativa, estrategia y orientaciones (UE, ES, OMS, FDA, OCDE)",
    "4": "Documentación interna NEXORA Salud (ficticia)",
}

MIN_PDF_SIZE = 5_000  # bytes: descartamos HTML de error o PDFs vacíos


# ═══════════════════════════════════════════════════════════════════════════
# DESCARGA
# ═══════════════════════════════════════════════════════════════════════════

def download_pdf(url: str, filepath: Path, timeout: int = 60) -> Tuple[bool, int]:
    """Descarga una URL a filepath. Devuelve (éxito, tamaño_bytes)."""
    try:
        resp = requests.get(
            url,
            headers=HEADERS,
            timeout=timeout,
            allow_redirects=True,
            stream=True,
        )
        resp.raise_for_status()

        # Validación ligera: debería ser PDF (o al menos binario)
        content_type = resp.headers.get("Content-Type", "").lower()
        if "text/html" in content_type:
            # Probablemente una página de error disfrazada
            return False, 0

        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        size = filepath.stat().st_size
        if size < MIN_PDF_SIZE:
            filepath.unlink(missing_ok=True)
            return False, 0

        # Validación del magic number del PDF
        with open(filepath, "rb") as f:
            header = f.read(5)
        if not header.startswith(b"%PDF"):
            filepath.unlink(missing_ok=True)
            return False, 0

        return True, size

    except Exception:
        filepath.unlink(missing_ok=True)
        return False, 0


def try_download_web(urls: List[str], filepath: Path,
                     skip_existing: bool) -> Tuple[str, int]:
    """Intenta descargar desde la lista de URLs. Devuelve (status, size)."""
    if skip_existing and filepath.exists() and filepath.stat().st_size > MIN_PDF_SIZE:
        return "SKIP", filepath.stat().st_size

    for i, url in enumerate(urls):
        label = "" if i == 0 else f" [alt {i}]"
        short_url = url if len(url) <= 80 else url[:77] + "..."
        print(f"    →{label} {short_url}", end=" ", flush=True)

        ok, size = download_pdf(url, filepath)
        if ok:
            print(f"✓ ({size // 1024} KB)")
            return "OK", size
        print("✗")
        time.sleep(0.3)

    return "FAIL", 0


def try_copy_local(source_name: str, dest_path: Path,
                   search_dirs: List[Path],
                   skip_existing: bool) -> Tuple[str, int]:
    """Busca un fichero local en los directorios y lo copia a dest_path."""
    if skip_existing and dest_path.exists() and dest_path.stat().st_size > 1000:
        return "SKIP", dest_path.stat().st_size

    for search_dir in search_dirs:
        source = search_dir / source_name
        if source.exists():
            shutil.copy2(source, dest_path)
            size = dest_path.stat().st_size
            print(f"    → copia desde {search_dir}/ ✓ ({size // 1024} KB)")
            return "OK", size

    print(f"    → no encontrado en ninguna carpeta de búsqueda ✗")
    return "NOT_FOUND", 0


# ═══════════════════════════════════════════════════════════════════════════
# CARGA DEL INVENTARIO
# ═══════════════════════════════════════════════════════════════════════════

def load_inventario(csv_path: Path) -> List[dict]:
    """Lee el CSV y lo valida mínimamente."""
    if not csv_path.exists():
        print(f"ERROR: inventario no encontrado: {csv_path}")
        sys.exit(1)

    required = {"id", "filename", "titulo", "capa", "categoria",
                "fuente", "tipo_descarga", "urls"}

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        if not required.issubset(reader.fieldnames or []):
            missing = required - set(reader.fieldnames or [])
            print(f"ERROR: columnas obligatorias ausentes en CSV: {missing}")
            sys.exit(1)
        rows = [row for row in reader if row["filename"].strip()]

    # Validación ligera
    for r in rows:
        if r["tipo_descarga"] not in ("web", "local"):
            print(f"ERROR: tipo_descarga inválido '{r['tipo_descarga']}' "
                  f"en fila {r['id']}")
            sys.exit(1)

    return rows


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Descarga un corpus de PDFs definido en un CSV de inventario"
    )
    parser.add_argument("--inventario", default="corpus_inventario.csv",
                        help="Ruta al CSV de inventario")
    parser.add_argument("--output-dir", default="./nexora_salud_corpus",
                        help="Carpeta destino de los PDFs")
    parser.add_argument("--local-docs-dir", default=".",
                        help="Carpeta donde buscar documentos de tipo 'local' "
                             "(ej. PDFs NEXORA internos)")
    parser.add_argument("--skip-existing", action="store_true",
                        help="No re-descargar ficheros que ya existan")
    parser.add_argument("--only-capa", default="",
                        help="Filtrar por capas (ej. '1,2')")
    parser.add_argument("--only-ids", default="",
                        help="Filtrar por IDs (ej. '28,54,55,61')")
    parser.add_argument("--only-categoria", default="",
                        help="Filtrar por categorías "
                             "(ej. 'Endocrinologia,Regulacion_UE')")
    parser.add_argument("--list-categorias", action="store_true",
                        help="Lista las categorías disponibles y sale")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    inventario = load_inventario(Path(args.inventario))

    # Listar categorías y salir
    if args.list_categorias:
        from collections import Counter
        cats = Counter(r["categoria"] for r in inventario)
        print(f"\n  Categorías disponibles ({len(cats)}):\n")
        for cat, n in sorted(cats.items()):
            print(f"    {n:3d}  {cat}")
        print()
        return

    # Filtros opcionales
    if args.only_capa:
        capas_filter = {c.strip() for c in args.only_capa.split(",") if c.strip()}
        inventario = [r for r in inventario if r["capa"] in capas_filter]
    if args.only_ids:
        ids_filter = {i.strip() for i in args.only_ids.split(",") if i.strip()}
        inventario = [r for r in inventario if r["id"] in ids_filter]
    if args.only_categoria:
        cats_filter = {c.strip() for c in args.only_categoria.split(",") if c.strip()}
        inventario = [r for r in inventario if r["categoria"] in cats_filter]

    if not inventario:
        print("⚠ El filtro aplicado no deja ningún documento para descargar.")
        return

    # Directorios de búsqueda para ficheros locales
    local_search = [
        Path(args.local_docs_dir),
        Path(args.local_docs_dir) / "nexora_salud_corpus",
        Path("./nexora_salud_interno"),          # documentos internos generados
        Path("./ContentRAG_Salud/AllFiles"),     # guías retiradas del catálogo público
        Path.home() / "nexora_salud_corpus",
        Path.home() / "Desktop" / "nexora_salud_corpus",
        output_dir,
    ]

    # Separar por tipo para imprimir ordenadamente
    inventario_web = [r for r in inventario if r["tipo_descarga"] == "web"]
    inventario_local = [r for r in inventario if r["tipo_descarga"] == "local"]

    print()
    print("=" * 72)
    print("  DESCARGA DE CORPUS — genérico por CSV")
    print("=" * 72)
    print(f"  Inventario:  {Path(args.inventario).resolve()}")
    print(f"  Destino:     {output_dir.resolve()}")
    print(f"  Documentos:  {len(inventario)} "
          f"(web: {len(inventario_web)}, local: {len(inventario_local)})")
    if args.skip_existing:
        print(f"  Modo:        skip-existing")
    print()

    results = []
    counts = {"OK": 0, "SKIP": 0, "FAIL": 0, "NOT_FOUND": 0}
    total_size = 0

    # ── Descarga web ────────────────────────────────────────────────────────
    current_capa = None
    for row in inventario_web:
        if row["capa"] != current_capa:
            current_capa = row["capa"]
            capa_name = CAPA_NAMES.get(current_capa, f"Capa {current_capa}")
            print(f"\n{'─' * 72}")
            print(f"  CAPA {current_capa}: {capa_name}")
            print(f"{'─' * 72}")

        urls = [u.strip() for u in row["urls"].split("|") if u.strip()]
        filepath = output_dir / row["filename"]

        print(f"\n  📄 [{row['id']}] {row['filename']}")
        print(f"     {row['titulo']}")
        print(f"     [{row['categoria']}]")

        status, size = try_download_web(urls, filepath, args.skip_existing)
        counts[status] += 1
        total_size += size

        if status == "SKIP":
            print(f"    ⏭ Ya existe ({size // 1024} KB)")

        results.append({
            "id": row["id"],
            "filename": row["filename"],
            "titulo": row["titulo"],
            "capa": row["capa"],
            "categoria": row["categoria"],
            "fuente": row["fuente"],
            "tipo_descarga": row["tipo_descarga"],
            "url_usada": urls[0] if urls else "",
            "estado": status,
            "size_bytes": size,
        })

        time.sleep(0.3)

    # ── Copia local ─────────────────────────────────────────────────────────
    if inventario_local:
        print(f"\n{'─' * 72}")
        print(f"  CAPA 4 — documentación interna (copia local)")
        print(f"{'─' * 72}")

        for row in inventario_local:
            source_name = row["urls"].strip()  # en local, urls contiene el nombre
            dest_path = output_dir / row["filename"]

            print(f"\n  📄 [{row['id']}] {row['filename']}")
            print(f"     {row['titulo']}")
            print(f"     [{row['categoria']}]")
            print(f"     Buscando: {source_name}")

            status, size = try_copy_local(
                source_name, dest_path, local_search, args.skip_existing
            )
            counts[status] += 1
            total_size += size

            if status == "SKIP":
                print(f"    ⏭ Ya existe ({size // 1024} KB)")
            elif status == "NOT_FOUND":
                print(f"    ⚠ Generar con generar_corpus_nexora_salud.py "
                      f"o ubicar manualmente")

            results.append({
                "id": row["id"],
                "filename": row["filename"],
                "titulo": row["titulo"],
                "capa": row["capa"],
                "categoria": row["categoria"],
                "fuente": row["fuente"],
                "tipo_descarga": row["tipo_descarga"],
                "url_usada": f"local:{source_name}",
                "estado": status,
                "size_bytes": size,
            })

    # ── CSV de resultados ───────────────────────────────────────────────────
    results_csv = output_dir / "corpus_resultados.csv"
    with open(results_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["id", "filename", "titulo", "capa", "categoria",
                        "fuente", "tipo_descarga", "url_usada",
                        "estado", "size_bytes"],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(results)

    # ── Reporte final ───────────────────────────────────────────────────────
    total_pdfs = len(list(output_dir.glob("*.pdf")))
    pendientes = [(r["filename"], r["titulo"])
                  for r in results if r["estado"] in ("FAIL", "NOT_FOUND")]

    print(f"\n{'=' * 72}")
    print(f"  REPORTE FINAL")
    print(f"{'=' * 72}")
    print(f"  ✓ Descargados/copiados:  {counts['OK']}")
    if counts["SKIP"]:
        print(f"  ⏭ Ya existían:          {counts['SKIP']}")
    if counts["FAIL"]:
        print(f"  ✗ Fallos de descarga:    {counts['FAIL']}")
    if counts["NOT_FOUND"]:
        print(f"  ✗ Locales no hallados:   {counts['NOT_FOUND']}")
    print()
    print(f"  📁 PDFs en carpeta:      {total_pdfs}")
    print(f"  💾 Tamaño total:         {total_size / (1024*1024):.1f} MB")
    print(f"  📄 Resultados:           {results_csv}")
    print(f"  📂 Directorio:           {output_dir.resolve()}")

    if pendientes:
        print(f"\n  ⚠ Pendientes ({len(pendientes)}):")
        for fn, titulo in pendientes:
            print(f"    • {fn}")
            print(f"        {titulo}")

    print(f"\n{'=' * 72}\n")


if __name__ == "__main__":
    main()