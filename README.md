# rag_nexora_salud

Corpus y pipeline de un **RAG sobre guías de práctica clínica, normativa sanitaria y
protocolos internos** para la asignatura *Inteligencia Artificial aplicada a Sectores
Productivos* (UNIR). Es la versión sanitaria de
[rag_nexora_legal](https://github.com/Lougedo/rag_nexora_legal).

> 📦 **Pesa unos 2 GB.** Si solo quieres los scripts o el práctico de clase, descarga el ZIP
> de la carpeta que necesites o haz un clon parcial:
> `git clone --filter=blob:none --sparse https://github.com/Lougedo/rag_nexora_salud`

> ⚠️ **Material docente.** NEXORA Salud es un grupo hospitalario **ficticio**. El corpus
> mezcla a propósito guías vigentes, caducadas, borradores y versiones resumidas para
> enseñar dónde falla un RAG. **Nada de esto sirve para tomar decisiones clínicas.**

---

## La dimensión del corpus

| | |
|---|---|
| Documentos | **984** PDF |
| Páginas | **31.088** |
| Texto | **97,4 millones** de caracteres · unos 16 millones de palabras |
| Tokens (aprox.) | **unos 24 millones** |
| Trozos (1.000 caracteres, solape 200) | **unos 122.000** |
| Peso | 2 GB |

**Para ponerlo en perspectiva:**

| Herramienta | Cuánto admite | ¿Cabe este corpus? |
|---|---|---|
| Una conversación con un modelo de 200.000 tokens de contexto | ~150.000 palabras | No: unas **120 veces** más grande |
| Un proyecto de Claude con búsqueda (RAG) activada | Hasta unas 10 veces su contexto | No: unas 12 veces más grande |
| Gemini Notebook gratuito / Plus / Pro | 50 / 100 / 300 fuentes por cuaderno | No: 984 fuentes |
| Gemini Notebook Ultra | 500-600 fuentes | No |
| Un RAG propio (este repositorio) | Lo que quepa en la base vectorial | Sí. Y un hospital real tendría más |

Cifras de límites a septiembre de 2026, sacadas de la documentación y de guías públicas de
cada producto; cambian a menudo.

---

## El corpus, por capas

| Capa | Qué contiene | Docs | Páginas |
|---|---|---|---|
| **1** | Guías de práctica clínica del SNS (versión completa), de GuíaSalud | 43 | 7.701 |
| **2** | Material complementario de esas guías: resúmenes, guías rápidas, herramientas, material metodológico, revisiones de vigencia, **borradores de exposición pública** y versiones en inglés | 44 | 4.424 |
| **3** | Normativa, estrategia y orientaciones: AI Act, MDR, IVDR, EHDS, RGPD, legislación farmacéutica de la UE, 65 leyes y reales decretos sanitarios del BOE, Estrategia de IA del SNS, 110 publicaciones de la OMS, FDA y OCDE | 207 | 8.148 |
| **4** | Documentos internos de **NEXORA Salud (ficticios)**, generados con `generar_corpus_nexora_salud.py` | 4 | 6 |
| **5** | Literatura científica en abierto (CC BY): 330 artículos de PLOS y 356 de Frontiers sobre IA en salud, modelos de lenguaje, apoyo a la decisión clínica y diabetes | 686 | 10.809 |

El detalle, documento a documento, está en [`corpus_inventario.csv`](corpus_inventario.csv).

### Las trampas que tiene a propósito

- **Una guía de 2008** (diabetes tipo 2) que su propia portada declara *pendiente de
  actualización*, junto a la de **diabetes tipo 1 de 2026**, con objetivos de hemoglobina
  glicada distintos.
- **Una guía marcada como caducada** (depresión en la infancia).
- **Borradores de exposición pública** junto a la versión final de la misma guía.
- **Resúmenes, guías rápidas y versiones en inglés** que repiten el contenido de la guía
  completa: el buscador puede traer tres veces lo mismo.
- **Un protocolo interno de 2024** que dice prevalecer sobre las guías externas, fija un
  objetivo de HbA1c para diabetes tipo 1 más laxo que la guía de 2026 y tiene su revisión
  vencida.
- **Una política interna de vigencia** que prohíbe usar guías de más de cinco años sin
  revisión.
- **El AI Act original** (obligaciones en 2027) junto a un informe del Ministerio sobre el
  Digital Omnibus que las aplaza a 2028.
- **Dos informes de la OMS escaneados**: PDF sin texto. Sin reconocimiento óptico (OCR), un
  RAG no ve nada en ellos.
- **Legislación que se cuela por la palabra «sanitario»** pero no trata de salud humana (por
  ejemplo, ayudas por vaciado sanitario en ganadería). Ruido real de una búsqueda por título.
- **Documentos en inglés** (OMS, FDA, OCDE, artículos) mezclados con los españoles.

Un RAG no resuelve ninguna de estas situaciones por sí solo. Esa es la lección.

---

## Estructura

```
rag_nexora_salud/
├── corpus_inventario.csv            ← 984 documentos: capa, categoría, fuente, URL
├── nexora_salud_corpus/             ← los 984 PDF (+ corpus_resultados.csv)
├── nexora_salud_interno/            ← los 4 PDF ficticios de NEXORA Salud
├── clase_s4/                        ← 2 guías de diabetes recortadas (práctico de clase)
├── descargar_corpus.py              ← descarga el corpus a partir del inventario
├── generar_corpus_nexora_salud.py   ← genera los documentos internos
├── indexar_corpus.py                ← indexa en ChromaDB (OpenAI + Ollama local)
├── index_pdfs.py                    ← versión simple de abril (OpenAI)
├── index_pdfs_ollama.py             ← versión simple de abril (Ollama local)
├── herramientas/
│   ├── construir_inventario.py      ← base del inventario (capas 1-4) desde GuíaSalud
│   ├── ampliar_corpus.py            ← ampliación: BOE, EUR-Lex, OMS, PLOS y Frontiers
│   └── estadisticas_corpus.py       ← recuento de páginas, tokens y trozos
├── chatflows/                       ← chatflows de Flowise (OpenAI y Ollama)
├── n8n/                             ← flujo de n8n del práctico + encargo del montaje multimotor
├── docs/                            ← guía del pipeline, diseño del corpus y estadísticas
├── index.html                       ← webapp de demo para los chatflows de Flowise
└── specs_stack_rag_flowise.md       ← especificaciones del stack local
```

---

## Tres formas de usarlo

### 1 · n8n en la nube (sesión 4, en clase)

Sin instalar nada. Importa [`n8n/IASP_S4_RAG_guias_clinicas.json`](n8n/IASP_S4_RAG_guias_clinicas.json),
crea la credencial de Gemini y sube las dos guías de [`clase_s4/`](clase_s4/). El paso a
paso, con experimentos, está en la guía del aula virtual.

El montaje **multimotor** (OpenAI, Gemini y Ollama Cloud intercambiables, más un laboratorio
de embeddings) se construye con el MCP de n8n siguiendo
[`n8n/INSTRUCCIONES_MCP_RAG_multimotor.md`](n8n/INSTRUCCIONES_MCP_RAG_multimotor.md).

> **Ollama Cloud no ofrece modelos de embeddings**, solo de chat. En el montaje multimotor,
> Ollama redacta y los vectores los pone otro proveedor.

### 2 · Flowise + ChromaDB en local (sesión 5)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install requests reportlab chromadb pypdf tqdm \
            langchain langchain-community langchain-text-splitters \
            langchain-openai langchain-ollama langchain-chroma

python generar_corpus_nexora_salud.py      # documentos internos (ya incluidos)
python descargar_corpus.py --skip-existing # el corpus (ya incluido)

ollama pull nomic-embed-text               # embeddings locales
export OPENAI_API_KEY=...                  # solo si indexas con OpenAI
python indexar_corpus.py                   # colecciones nexora_salud_openai y nexora_salud_ollama

npx flowise start                          # e importa los JSON de chatflows/
```

> Indexar el corpus completo son unos 122.000 trozos. Con OpenAI (`text-embedding-3-small`)
> son unos 24 millones de tokens (en torno a 0,50 $ a la tarifa pública de 0,02 $ por millón)
> y tarda un buen rato. Con Ollama en un portátil puede tardar días. Para empezar con un
> subconjunto:
>
> ```bash
> python descargar_corpus.py --only-capa 1 --only-categoria Endocrinologia --output-dir ./mini
> python indexar_corpus.py --corpus-dir ./mini
> ```

Más detalle en [`docs/GUIA_PIPELINE_RAG.md`](docs/GUIA_PIPELINE_RAG.md).

### 3 · Para comparar con Gemini Notebook o un proyecto de Claude

Intenta subir el corpus entero a cualquiera de los dos. No cabe, ni de lejos. Sube las dos guías de
`clase_s4/` y haz las mismas preguntas que al RAG: ¿citan igual? ¿distinguen tipo 1 de
tipo 2? ¿avisan de que la guía de 2008 está pendiente de actualizar?

---

## Fuentes y licencias

Los documentos de las capas 1 a 3 son **publicaciones oficiales de acceso público**, y los de
la capa 5, **artículos científicos con licencia CC BY 4.0**. Se
redistribuyen aquí sin modificar, con fines exclusivamente docentes y sin ánimo de lucro, y
cada uno conserva su autoría y su licencia de origen:

- **GuíaSalud / Ministerio de Sanidad** — guías de práctica clínica del SNS:
  <https://portal.guiasalud.es/gpc/>
- **EUR-Lex** — legislación de la Unión Europea: <https://eur-lex.europa.eu>
- **BOE** — legislación española consolidada: <https://www.boe.es>
- **Ministerio de Sanidad** — Estrategia de IA del SNS:
  <https://www.sanidad.gob.es/areas/saludDigital/estrategiaIASNS/home.htm>
- **Organización Mundial de la Salud** — publicaciones con licencia CC BY-NC-SA 3.0 IGO:
  <https://iris.who.int>
- **FDA** — documentos del Gobierno de EE. UU.: <https://www.fda.gov>
- **OCDE** — <https://www.oecd.org>
- **PLOS** — artículos con licencia CC BY 4.0: <https://plos.org>
- **Frontiers** — artículos con licencia CC BY 4.0: <https://www.frontiersin.org>

La URL exacta de cada documento está en `corpus_inventario.csv`. Si eres titular de algún
documento y prefieres que no esté aquí, abre una *issue* y se retira.

**Licencia de este repositorio:** los scripts, la documentación y los documentos ficticios de
**NEXORA Salud** (capa 4) se publican bajo [CC0 1.0](LICENSE). La licencia CC0 **no se
aplica** a los documentos de terceros de las capas 1, 2, 3 y 5, que mantienen la licencia y los
derechos de sus autores.

**Nada de este repositorio constituye consejo médico.**
