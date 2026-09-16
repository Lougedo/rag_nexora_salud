#!/usr/bin/env python3
"""
indexar_corpus.py
=================
Indexa los PDFs de ./nexora_salud_corpus/ en ChromaDB con embeddings en
paralelo de OpenAI y Ollama. Crea dos colecciones:

    - nexora_salud_openai   (text-embedding-3-small, 1536 dim)
    - nexora_salud_ollama   (nomic-embed-text, 768 dim)

Dos modos de ChromaDB:
    --mode local   (default)  →  PersistentClient en ./chroma_db/
    --mode cloud              →  CloudClient contra Chroma Cloud SaaS

Los metadatos se enriquecen con la info de corpus_inventario.csv
(id, titulo, capa, categoria, fuente) para permitir filtros por capa (guía, complementario, normativa, interno)
y citas precisas en las respuestas del RAG.

Uso:
    # 1. Instala dependencias:
    pip install langchain langchain-community langchain-text-splitters \
                langchain-openai langchain-ollama langchain-chroma \
                chromadb pypdf tqdm

    # 2. Ollama corriendo con el modelo:
    ollama pull nomic-embed-text

    # 3. API keys en variables de entorno (nunca hardcoded):
    #    $env:OPENAI_API_KEY = "sk-..."
    #    $env:CHROMA_API_KEY = "ck-..."       (solo para --mode cloud)
    #    $env:CHROMA_TENANT  = "tu-tenant"    (opcional, se autodetecta)
    #    $env:CHROMA_DATABASE = "default_database" (opcional)

    # 4. Lanzar:
    python indexar_corpus.py                                  # local
    python indexar_corpus.py --mode cloud                     # Chroma Cloud
    python indexar_corpus.py --only ollama --mode cloud       # solo un proveedor
    python indexar_corpus.py --openai-model large
    python indexar_corpus.py --reset                          # borra y reindexa
    python indexar_corpus.py --chunk-size 1500 --chunk-overlap 300
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List

try:
    import chromadb
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_openai import OpenAIEmbeddings
    from langchain_ollama import OllamaEmbeddings
    from langchain_chroma import Chroma
    from langchain_core.documents import Document
    from tqdm import tqdm
except ImportError as e:
    missing = getattr(e, "name", str(e))
    print(f"ERROR: falta dependencia '{missing}'. Instala con:")
    print("  pip install langchain langchain-community langchain-text-splitters \\")
    print("              langchain-openai langchain-ollama langchain-chroma \\")
    print("              chromadb pypdf tqdm")
    sys.exit(1)


OPENAI_MODELS = {
    "small": "text-embedding-3-small",   # 1536 dim, ~$0.02/1M tokens
    "large": "text-embedding-3-large",   # 3072 dim, ~$0.13/1M tokens
}

COLLECTIONS = {
    "openai": "nexora_salud_openai",
    "ollama": "nexora_salud_ollama",
}

# Chroma Cloud (Starter / free tier) limita metadatos por registro (p. ej. 32
# claves en Upsert). PyPDFLoader añade decenas de claves del PDF; hay que
# quedarse solo con las que usa el RAG / Flowise.
CLOUD_METADATA_KEYS = frozenset({
    "source_file",
    "page",
    "chunk_index",
    "chunk_id",
    "source",
    "id",
    "titulo",
    "capa",
    "categoria",
    "fuente",
})


def _chromadb_scalar_metadata(v):
    if v is None:
        return None
    if isinstance(v, (str, int, float, bool)):
        return v
    return str(v)


def filtrar_metadatos_cloud(docs: List[Document]) -> None:
    """In-place: solo claves permitidas para no superar la cuota de Chroma Cloud."""
    for d in docs:
        new_md = {}
        for k in CLOUD_METADATA_KEYS:
            if k not in d.metadata:
                continue
            val = _chromadb_scalar_metadata(d.metadata[k])
            if val is not None and val != "":
                new_md[k] = val
        d.metadata = new_md


# ═══════════════════════════════════════════════════════════════════════════
# CARGA Y TROCEADO (secuencial, compartido entre proveedores)
# ═══════════════════════════════════════════════════════════════════════════

def cargar_inventario(csv_path: Path) -> Dict[str, dict]:
    """Indexa corpus_inventario.csv por filename para enriquecer metadatos."""
    if not csv_path.exists():
        return {}
    result: Dict[str, dict] = {}
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            result[row["filename"]] = {
                "id": row.get("id", ""),
                "titulo": row.get("titulo", ""),
                "capa": row.get("capa", ""),
                "categoria": row.get("categoria", ""),
                "fuente": row.get("fuente", ""),
            }
    return result


def cargar_y_trocear(corpus_dir: Path, inventario: Dict[str, dict],
                     chunk_size: int, chunk_overlap: int) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    pdfs = sorted(corpus_dir.glob("*.pdf"))
    if not pdfs:
        print(f"ERROR: no hay PDFs en {corpus_dir}/")
        sys.exit(1)

    print(f"\n Cargando y troceando {len(pdfs)} PDFs de {corpus_dir}/")
    docs: List[Document] = []
    saltados: List[str] = []

    for pdf in tqdm(pdfs, desc="  PDFs", unit="pdf"):
        meta_base = {"source_file": pdf.name, **inventario.get(pdf.name, {})}
        try:
            pages = PyPDFLoader(str(pdf)).load()
        except Exception as e:
            saltados.append(f"{pdf.name}: {e}")
            continue

        for page in pages:
            page.metadata.update(meta_base)

        chunks = splitter.split_documents(pages)
        for i, c in enumerate(chunks):
            c.metadata["chunk_index"] = i
            c.metadata["chunk_id"] = f"{pdf.name}::c{i:04d}"
            # normaliza el 'source' de PyPDFLoader al filename corto
            c.metadata["source"] = pdf.name
        docs.extend(chunks)

    if saltados:
        print(f"\n  ⚠ PDFs saltados ({len(saltados)}):")
        for s in saltados:
            print(f"     - {s}")

    return docs


# ═══════════════════════════════════════════════════════════════════════════
# INDEXACIÓN
# ═══════════════════════════════════════════════════════════════════════════

def preflight(embeddings, label: str) -> None:
    """Intenta embeddear un texto corto para fallar rápido ante auth/conexión."""
    try:
        embeddings.embed_query("ping")
    except Exception as e:
        raise RuntimeError(f"[{label}] fallo en preflight: {e}") from e


def build_chroma_client(args):
    """Crea un PersistentClient local o un CloudClient según --mode."""
    if args.mode == "cloud":
        api_key = os.getenv("CHROMA_API_KEY")
        if not api_key:
            print("ERROR: --mode cloud requiere CHROMA_API_KEY en el entorno.")
            print("  $env:CHROMA_API_KEY = \"ck-...\"")
            sys.exit(1)
        tenant = os.getenv("CHROMA_TENANT")
        database = os.getenv("CHROMA_DATABASE")
        kwargs = {"api_key": api_key}
        if tenant:
            kwargs["tenant"] = tenant
        if database:
            kwargs["database"] = database
        return chromadb.CloudClient(**kwargs), f"Chroma Cloud ({database or 'default'})"

    db_dir = Path(args.db_dir)
    db_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(db_dir)), f"local:{db_dir.resolve()}"


def indexar_en_chroma(docs: List[Document], embeddings, collection_name: str,
                      client, batch_size: int, label: str) -> dict:
    t0 = time.time()
    vs = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        client=client,
    )

    total = len(docs)
    ids = [d.metadata["chunk_id"] for d in docs]

    for i in range(0, total, batch_size):
        batch = docs[i : i + batch_size]
        batch_ids = ids[i : i + batch_size]
        vs.add_documents(batch, ids=batch_ids)
        done = min(i + batch_size, total)
        print(f"  [{label}] {done}/{total} chunks", flush=True)

    return {"collection": collection_name, "chunks": total, "elapsed": time.time() - t0}


def reset_colecciones(client, names: List[str]) -> None:
    for name in names:
        try:
            client.delete_collection(name)
            print(f"  Coleccion '{name}' eliminada")
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def parse_args():
    parser = argparse.ArgumentParser(
        description="Indexa el corpus NEXORA Salud en ChromaDB (OpenAI + Ollama en paralelo)"
    )
    parser.add_argument("--corpus-dir", default="./nexora_salud_corpus")
    parser.add_argument("--inventario", default="./corpus_inventario.csv")
    parser.add_argument("--db-dir", default="./chroma_db",
                        help="Directorio para modo local (ignorado en cloud)")
    parser.add_argument("--mode", choices=["local", "cloud"], default="local",
                        help="local=PersistentClient, cloud=Chroma Cloud")
    parser.add_argument("--only", choices=["openai", "ollama", "both"], default="both")
    parser.add_argument("--openai-model", choices=["small", "large"], default="small")
    parser.add_argument("--ollama-host", default="http://localhost:11434")
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--chunk-overlap", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--reset", action="store_true",
                        help="Borra las colecciones antes de reindexar")
    return parser.parse_args()


def build_jobs(args, providers: List[str]) -> List[dict]:
    jobs = []
    for p in providers:
        if p == "openai":
            model = OPENAI_MODELS[args.openai_model]
            jobs.append({
                "label": f"openai:{args.openai_model}",
                "collection": COLLECTIONS["openai"],
                "embeddings": OpenAIEmbeddings(model=model),
            })
        else:
            jobs.append({
                "label": "ollama:nomic",
                "collection": COLLECTIONS["ollama"],
                "embeddings": OllamaEmbeddings(
                    model="nomic-embed-text",
                    base_url=args.ollama_host,
                ),
            })
    return jobs


def ejecutar_paralelo(jobs: List[dict], docs: List[Document], client,
                      batch_size: int) -> dict:
    results = {}
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = {
            pool.submit(
                indexar_en_chroma, docs, j["embeddings"], j["collection"],
                client, batch_size, j["label"],
            ): j for j in jobs
        }
        for fut in as_completed(futures):
            j = futures[fut]
            try:
                results[j["label"]] = ("OK", fut.result())
            except Exception as e:
                results[j["label"]] = ("ERROR", str(e))
    return results


def imprimir_reporte(results: dict, elapsed: float, backend_desc: str) -> None:
    print(f"\n{'=' * 72}")
    print("  REPORTE")
    print(f"{'=' * 72}")
    for label, (status, info) in results.items():
        if status == "OK":
            print(f"  OK {label}: {info['chunks']} chunks  "
                  f"en {info['elapsed']:.1f}s  ({info['collection']})")
        else:
            print(f"  ERR {label}: {info}")
    print(f"\n  Total: {elapsed:.1f}s")
    print(f"  Backend: {backend_desc}")
    print(f"{'=' * 72}\n")


def main():
    args = parse_args()

    if args.only in ("openai", "both") and not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY no esta definida.")
        print("  PowerShell: $env:OPENAI_API_KEY = \"sk-...\"")
        print("  O usa --only ollama para saltarte OpenAI.")
        sys.exit(1)

    inventario = cargar_inventario(Path(args.inventario))
    print(f" Inventario: {len(inventario)} entradas cargadas"
          if inventario else " Sin inventario, metadatos minimos")

    docs = cargar_y_trocear(
        Path(args.corpus_dir), inventario, args.chunk_size, args.chunk_overlap
    )
    print(f"\n {len(docs)} chunks generados "
          f"(chunk_size={args.chunk_size}, overlap={args.chunk_overlap})")

    if args.mode == "cloud":
        filtrar_metadatos_cloud(docs)
        nkeys = max((len(d.metadata) for d in docs), default=0)
        print(f"\n Modo cloud: metadatos recortados a <= {nkeys} claves "
              f"(max {len(CLOUD_METADATA_KEYS)} definidas; cuota Chroma Cloud).")

    client, backend_desc = build_chroma_client(args)
    print(f"\n Backend ChromaDB: {backend_desc}")

    providers = ["openai", "ollama"] if args.only == "both" else [args.only]
    if args.reset:
        reset_colecciones(client, [COLLECTIONS[p] for p in providers])

    jobs = build_jobs(args, providers)

    print("\n Preflight embeddings...")
    for j in jobs:
        try:
            preflight(j["embeddings"], j["label"])
            print(f"  OK [{j['label']}]")
        except Exception as e:
            print(f"  FAIL [{j['label']}] {e}")
            sys.exit(1)

    print(f"\n Indexando en paralelo: {', '.join(j['label'] for j in jobs)}")
    print("=" * 72)
    t0 = time.time()
    results = ejecutar_paralelo(jobs, docs, client, args.batch_size)
    imprimir_reporte(results, time.time() - t0, backend_desc)


if __name__ == "__main__":
    main()
