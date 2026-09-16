"""
Script de indexación de PDFs en ChromaDB con OpenAI Embeddings
==============================================================
Procesa cada PDF de una carpeta uno a uno, trocea, genera embeddings
con OpenAI y los guarda en ChromaDB persistente en disco.

Después, Flowise se conecta a ChromaDB para consultar.

Uso:
    pip install chromadb langchain langchain-openai langchain-chroma langchain-community pypdf
    export OPENAI_API_KEY="tu-api-key-aqui"
    python indexar_pdfs.py
"""

import os
import sys
import time
from pathlib import Path

# --- CONFIGURACIÓN ---
CARPETA_PDFS = "/Users/javier.lougedo/Documents/Presentaciones/IAaSP/Flowise/ContentRAG_Salud/AllFiles"  # Cambia a tu carpeta
CHROMA_PERSIST_DIR = "./chroma_guias_clinicas"            # Donde se guarda la DB
COLLECTION_NAME = "guias_clinicas"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 50  # Chunks por llamada a OpenAI (evita el límite de 300K tokens)
# ---------------------

def main():
    # Verificar API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Falta OPENAI_API_KEY. Ejecuta:")
        print('   export OPENAI_API_KEY="tu-api-key-aqui"')
        sys.exit(1)

    # Imports (después de verificar que están instalados)
    try:
        from langchain_community.document_loaders import PyPDFLoader
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_openai import OpenAIEmbeddings
        from langchain_chroma import Chroma
    except ImportError as e:
        print(f"❌ Falta dependencia: {e}")
        print("Ejecuta:")
        print("  pip install chromadb langchain langchain-openai langchain-chroma langchain-community pypdf")
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
    print(f"🔤 Modelo embeddings: {EMBEDDING_MODEL}")
    print(f"✂️  Chunk size: {CHUNK_SIZE}, overlap: {CHUNK_OVERLAP}")
    print(f"📦 Batch size: {BATCH_SIZE} chunks por llamada")
    print("=" * 60)

    # Inicializar componentes
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

    # Crear o abrir ChromaDB
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_PERSIST_DIR,
    )

    total_chunks = 0
    errores = []

    for i, pdf_path in enumerate(pdfs, 1):
        nombre = pdf_path.name
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

            # Añadir metadata del nombre del archivo a cada chunk
            for chunk in chunks:
                chunk.metadata["source_file"] = nombre

            # Insertar en batches para no superar el límite de OpenAI
            for batch_start in range(0, len(chunks), BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, len(chunks))
                batch = chunks[batch_start:batch_end]

                vectorstore.add_documents(batch)

                print(f"   📦 Batch {batch_start+1}-{batch_end} de {len(chunks)} indexado")

                # Pausa breve entre batches para no saturar la API
                if batch_end < len(chunks):
                    time.sleep(1)

            total_chunks += len(chunks)
            print(f"   ✅ Completado ({total_chunks} chunks totales)")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            errores.append((nombre, str(e)))
            continue

    # Resumen final
    print("\n" + "=" * 60)
    print(f"🏁 INDEXACIÓN COMPLETADA")
    print(f"   📄 PDFs procesados: {len(pdfs) - len(errores)}/{len(pdfs)}")
    print(f"   📦 Chunks totales:  {total_chunks}")
    print(f"   💾 Guardado en:     {CHROMA_PERSIST_DIR}")

    if errores:
        print(f"\n   ⚠️  Errores ({len(errores)}):")
        for nombre, error in errores:
            print(f"      - {nombre}: {error}")

    print(f"\n🔗 Para conectar desde Flowise:")
    print(f"   1. Levanta ChromaDB: chroma run --path {CHROMA_PERSIST_DIR} --port 8000")
    print(f"   2. En Flowise usa el nodo 'Chroma' con:")
    print(f"      - URL: http://localhost:8000")
    print(f"      - Collection: {COLLECTION_NAME}")
    print(f"      - Embeddings: OpenAI ({EMBEDDING_MODEL})")


if __name__ == "__main__":
    main()