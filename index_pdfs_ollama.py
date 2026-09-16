"""
Script de indexación de PDFs en ChromaDB con Ollama Embeddings (LOCAL)
=====================================================================
Igual que el script de OpenAI pero usando Ollama local.
Genera embeddings con nomic-embed-text, guarda en ChromaDB en disco.

Uso:
    source ~/flowise-rag/bin/activate
    python indexar_pdfs_ollama.py
"""

import os
import sys
import time
from pathlib import Path

# --- CONFIGURACIÓN ---
CARPETA_PDFS = "/Users/javier.lougedo/Documents/Presentaciones/IAaSP/Flowise/ContentRAG_Salud/AllFiles"  # Cambia a tu carpeta
CHROMA_PERSIST_DIR = "./chroma_guias_ollama"              # DB separada de la de OpenAI
COLLECTION_NAME = "guias_clinicas_ollama"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "nomic-embed-text"
BATCH_SIZE = 25  # Ollama no tiene límite estricto pero batches pequeños son más estables
# ---------------------

def main():
    # Verificar que Ollama está corriendo
    import urllib.request
    try:
        urllib.request.urlopen(OLLAMA_BASE_URL)
    except Exception:
        print(f"❌ Ollama no está corriendo en {OLLAMA_BASE_URL}")
        print("   Abre la app Ollama o ejecuta: ollama serve")
        sys.exit(1)

    # Imports
    try:
        from langchain_community.document_loaders import PyPDFLoader
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_community.embeddings import OllamaEmbeddings
        from langchain_chroma import Chroma
    except ImportError as e:
        print(f"❌ Falta dependencia: {e}")
        print("Ejecuta:")
        print("  pip install chromadb langchain langchain-chroma langchain-community pypdf")
        sys.exit(1)

    # Buscar PDFs
    carpeta = Path(CARPETA_PDFS)
    pdfs = sorted(carpeta.glob("*.pdf"))

    if not pdfs:
        print(f"❌ No hay PDFs en {CARPETA_PDFS}")
        sys.exit(1)

    print(f"📂 Carpeta: {CARPETA_PDFS}")
    print(f"📄 PDFs encontrados: {len(pdfs)}")
    print(f"💾 ChromaDB se guardará en: {CHROMA_PERSIST_DIR}")
    print(f"🤖 Embeddings: Ollama ({EMBEDDING_MODEL}) — 100% LOCAL")
    print(f"✂️  Chunk size: {CHUNK_SIZE}, overlap: {CHUNK_OVERLAP}")
    print(f"📦 Batch size: {BATCH_SIZE} chunks por llamada")
    print("=" * 60)

    # Inicializar componentes
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    embeddings = OllamaEmbeddings(
        model=EMBEDDING_MODEL,
        base_url=OLLAMA_BASE_URL,
    )

    # Crear o abrir ChromaDB
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_PERSIST_DIR,
    )

    total_chunks = 0
    errores = []
    start_time = time.time()

    for i, pdf_path in enumerate(pdfs, 1):
        nombre = pdf_path.name
        pdf_start = time.time()
        print(f"\n[{i}/{len(pdfs)}] 📄 {nombre}")

        try:
            # Cargar PDF
            loader = PyPDFLoader(str(pdf_path))
            pages = loader.load()
            print(f"   📖 Páginas cargadas: {len(pages)}")

            # Trocear
            chunks = text_splitter.split_documents(pages)
            print(f"   ✂️  Chunks generados: {len(chunks)}")

            if not chunks:
                print(f"   ⚠️  Sin contenido, saltando...")
                continue

            # Añadir metadata
            for chunk in chunks:
                chunk.metadata["source_file"] = nombre

            # Insertar en batches
            for batch_start in range(0, len(chunks), BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, len(chunks))
                batch = chunks[batch_start:batch_end]

                vectorstore.add_documents(batch)

                print(f"   📦 Batch {batch_start+1}-{batch_end} de {len(chunks)} indexado")

            total_chunks += len(chunks)
            elapsed = time.time() - pdf_start
            print(f"   ✅ Completado en {elapsed:.1f}s ({total_chunks} chunks totales)")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            errores.append((nombre, str(e)))
            continue

    # Resumen final
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"🏁 INDEXACIÓN COMPLETADA en {total_time:.0f}s ({total_time/60:.1f} min)")
    print(f"   📄 PDFs procesados: {len(pdfs) - len(errores)}/{len(pdfs)}")
    print(f"   📦 Chunks totales:  {total_chunks}")
    print(f"   💾 Guardado en:     {CHROMA_PERSIST_DIR}")
    print(f"   💰 Coste:           0 € (todo local)")

    if errores:
        print(f"\n   ⚠️  Errores ({len(errores)}):")
        for nombre, error in errores:
            print(f"      - {nombre}: {error}")

    print(f"\n🔗 Para conectar desde Flowise:")
    print(f"   1. Levanta ChromaDB: chroma run --path {CHROMA_PERSIST_DIR} --port 8001")
    print(f"      (puerto 8001 para no chocar con el de OpenAI en 8000)")
    print(f"   2. En Flowise usa el nodo 'Chroma' con:")
    print(f"      - URL: http://localhost:8001")
    print(f"      - Collection: {COLLECTION_NAME}")
    print(f"      - Embeddings: Ollama Embeddings (nomic-embed-text)")
    print(f"   3. Chat Model: ChatOllama con phi4:14b o llama3.1:8b")


if __name__ == "__main__":
    main()