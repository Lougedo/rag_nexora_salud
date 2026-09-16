# Guía del pipeline RAG — NEXORA Salud

Resumen operativo: inventario → documentos internos → descarga → indexación → consulta
(n8n en la nube o Flowise en local).

---

## Arquitectura

```
  catálogo GuíaSalud ──┐
  normativa (fija) ────┼──> herramientas/construir_inventario.py ──> corpus_inventario.csv
  internos NEXORA ─────┘                                                   │
                                                                           ▼
  generar_corpus_nexora_salud.py ──> nexora_salud_interno/ ──┐     descargar_corpus.py
                                                             └────────────┤
                                                                          ▼
                                                           nexora_salud_corpus/ (122 PDF)
                                                                          │
                     ┌────────────────────────────────────────────────────┼─────────────────────┐
                     ▼                                                    ▼                     ▼
            indexar_corpus.py                                   n8n (Simple Vector       Gemini Notebook /
     ChromaDB: nexora_salud_openai (1.536)                      Store, en memoria)       proyecto de Claude
               nexora_salud_ollama  (768)                       clase_s4/ en clase       (para comparar)
                     │
                     ▼
            Flowise (chatflows/) ──> index.html
```

---

## Paso a paso

### 0 · Entorno

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install requests reportlab chromadb pypdf tqdm pymupdf \
            langchain langchain-community langchain-text-splitters \
            langchain-openai langchain-ollama langchain-chroma
```

Las claves van **siempre** en variables de entorno, nunca en el código:

```bash
export OPENAI_API_KEY="..."        # indexar con OpenAI
export CHROMA_API_KEY="..."        # solo con --mode cloud
```

### 1 · Inventario (opcional: ya viene hecho)

```bash
python herramientas/construir_inventario.py
```

Lee el catálogo público de GuíaSalud y añade la normativa y los documentos internos. Si
GuíaSalud publica guías nuevas, aparecerán solas. **Revisa el CSV antes de descargar:** los
números de documento cambian si cambia el catálogo.

### 2 · Documentos internos (opcional: ya vienen hechos)

```bash
python generar_corpus_nexora_salud.py
```

### 3 · Descarga (opcional: ya viene hecha)

```bash
python descargar_corpus.py --skip-existing
```

Descarga los documentos `web` y copia los `local` desde `nexora_salud_interno/`. Deja un
informe en `nexora_salud_corpus/corpus_resultados.csv`. Cuatro guías ya no están en el
catálogo público y se copian de disco: ver `herramientas/construir_inventario.py`.

### 4 · Indexación en ChromaDB

```bash
ollama pull nomic-embed-text
python indexar_corpus.py                        # local, OpenAI + Ollama
python indexar_corpus.py --only openai          # solo OpenAI
python indexar_corpus.py --mode cloud           # Chroma Cloud
python indexar_corpus.py --reset                # desde cero
python indexar_corpus.py --chunk-size 1500 --chunk-overlap 300
```

Los metadatos de cada trozo incluyen el id, el título, la capa, la categoría y la fuente del
inventario: se pueden usar para filtrar (por ejemplo, excluir la capa 2 o los borradores).

**Tiempos y costes orientativos** (corpus completo, unos 43.000 trozos y 8,6 millones de
tokens):

| Embeddings | Tiempo | Coste |
|---|---|---|
| OpenAI `text-embedding-3-small` | Minutos | Menos de 0,20 $ |
| Ollama `nomic-embed-text` en un portátil | Horas | 0 € |

### 5 · Consulta

- **Flowise:** `npx flowise start`, importa los JSON de `chatflows/`, asigna las
  credenciales y apunta el nodo Chroma a tu servidor (`chroma run --path ./chroma_db`).
- **n8n:** ver [`../n8n/`](../n8n/). En clase se usan solo las dos guías de `clase_s4/`,
  porque el almacén en memoria de n8n no está pensado para 43.000 trozos.

---

## Por qué dos colecciones

Cada modelo de embeddings produce vectores de un tamaño distinto (1.536 frente a 768) y con
un «mapa» propio. **No se puede consultar una colección con otro modelo.** Si cambias de
modelo de embeddings, tienes que volver a indexar.

El modelo que redacta sí se puede cambiar libremente. Por eso **Ollama Cloud**, que no ofrece
modelos de embeddings, puede redactar respuestas usando una colección indexada con OpenAI o
con Gemini.

---

## Problemas típicos

| Síntoma | Causa | Solución |
|---|---|---|
| `Dimension mismatch` en Chroma | Consulta con un modelo distinto al de indexar | Mismo modelo en las dos puntas |
| Descarga con `FAIL` | La URL ha cambiado | Actualiza la URL en el CSV, o regenera el inventario |
| Respuestas repetidas | Resumen, guía rápida y guía completa dicen lo mismo | Filtrar por `capa = 1` o deduplicar |
| El RAG cita un borrador | La capa 2 incluye borradores de exposición pública | Excluirlos por metadatos |
| Ollama no genera embeddings | Estás apuntando a Ollama Cloud | Los embeddings de Ollama solo funcionan en local |
