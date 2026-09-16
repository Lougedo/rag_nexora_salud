# Especificaciones Técnicas — Stack RAG con Flowise
## IASP S4 · IA en Salud · UNIR 2026

---

## 1. Flowise

| Campo | Detalle |
|---|---|
| **Qué es** | Plataforma open source para construir aplicaciones de IA visualmente (drag & drop) |
| **Versión utilizada** | 3.x (última estable vía npx) |
| **Licencia** | Apache 2.0 |
| **Requisitos** | Node.js v18.15+ o v20 LTS (recomendado). No usar v23 |
| **Puerto por defecto** | http://localhost:3000 |
| **Persistencia** | SQLite local en ~/.flowise (chatflows, credentials). Vector stores en memoria se pierden al reiniciar |
| **Web** | https://flowiseai.com |
| **Docs** | https://docs.flowiseai.com |
| **GitHub** | https://github.com/FlowiseAI/Flowise (36K+ stars) |

### Instalación y arranque

```bash
# Instalar Node.js 20 LTS (si no se tiene)
# macOS: brew install node@20
# Windows: descargar de https://nodejs.org

# Lanzar Flowise (se descarga automáticamente la primera vez)
npx flowise start

# Con seguridad de rutas desactivada (necesario para Folder Loader)
npx flowise start --PATH_TRAVERSAL_SAFETY=false

# En otro puerto
npx flowise start --PORT=3001
```

### Nodos principales utilizados en el RAG

- **ChatOpenAI** — conexión al API de OpenAI para chat
- **ChatOllama** — conexión a Ollama local para chat
- **OpenAI Embeddings** — genera embeddings vía API de OpenAI
- **Ollama Embeddings** — genera embeddings con Ollama local
- **Chroma** — conexión a ChromaDB como vector store
- **In-Memory Vector Store** — vector store en RAM (se pierde al reiniciar)
- **Conversational Retrieval QA Chain** — cadena RAG con historial de conversación
- **Pdf File** — carga un PDF individual
- **Folder with Files** — carga todos los archivos de una carpeta
- **Recursive Character Text Splitter** — trocea documentos en chunks

---

## 2. Ollama

| Campo | Detalle |
|---|---|
| **Qué es** | Runtime open source para ejecutar LLMs localmente |
| **Licencia** | MIT |
| **Plataformas** | macOS 11+, Windows 10+, Linux |
| **Puerto por defecto** | http://localhost:11434 |
| **Aceleración** | Apple Silicon (Metal), NVIDIA CUDA, AMD ROCm |
| **Web** | https://ollama.com |
| **Biblioteca de modelos** | https://ollama.com/library |

### Instalación

```bash
# macOS
# Descargar de https://ollama.com/download/mac (app con icono en barra de menú)

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# Descargar de https://ollama.com/download/windows

# Verificar
ollama --version
curl http://localhost:11434   # "Ollama is running"
```

### Comandos esenciales

```bash
ollama pull <modelo>      # Descargar modelo
ollama list               # Ver modelos instalados
ollama run <modelo>       # Chat interactivo (salir con /bye)
ollama ps                 # Ver modelos activos en memoria
ollama rm <modelo>        # Eliminar modelo
ollama serve              # Arrancar el servicio manualmente
```

---

## 3. Modelos de Ollama utilizados

### 3.1 nomic-embed-text (Embeddings)

| Campo | Detalle |
|---|---|
| **Propósito** | Generar embeddings (vectores numéricos) de texto |
| **Desarrollador** | Nomic AI |
| **Parámetros** | ~137M |
| **Dimensiones del vector** | 768 |
| **Contexto máximo** | 8.192 tokens |
| **Tamaño en disco** | ~274 MB |
| **RAM necesaria** | ~1 GB |
| **Licencia** | Apache 2.0 |
| **Uso en el RAG** | Convertir chunks de texto en vectores para ChromaDB |

```bash
ollama pull nomic-embed-text
```

**Nota importante:** Este modelo SOLO genera embeddings, no sirve para chat. En Flowise va en el nodo "Ollama Embeddings", nunca en "ChatOllama". Si se mezcla con un modelo de chat en el nodo de embeddings, ChromaDB dará error de dimensiones incompatibles.

### 3.2 phi4:14b (Chat — Alta calidad)

| Campo | Detalle |
|---|---|
| **Propósito** | Modelo de chat / generación de texto |
| **Desarrollador** | Microsoft |
| **Parámetros** | 14B |
| **Contexto máximo** | 16.384 tokens |
| **Cuantización** | Q4_K_M (por defecto en Ollama) |
| **Tamaño en disco** | ~9.1 GB |
| **RAM necesaria** | ~16 GB (mínimo), 18+ GB recomendado |
| **Licencia** | MIT |
| **Fortalezas** | Razonamiento, STEM, lógica, calidad cercana a modelos 2-3x mayores |
| **Debilidades** | Más lento que modelos pequeños, inglés mejor que español |
| **Uso en el RAG** | Modelo principal de chat en la variante Ollama |

```bash
ollama pull phi4:14b
```

**Rendimiento esperado en M3 Pro 18 GB:** Funciona cómodamente, deja ~9 GB libres para sistema. Velocidad de generación moderada (~8-15 tokens/segundo en CPU). Apple Silicon acelera con Metal automáticamente.

### 3.3 llama3.1:8b (Chat — Equilibrio)

| Campo | Detalle |
|---|---|
| **Propósito** | Modelo de chat / generación de texto |
| **Desarrollador** | Meta |
| **Parámetros** | 8B |
| **Contexto máximo** | 128.000 tokens |
| **Cuantización** | Q4_K_M (por defecto) |
| **Tamaño en disco** | ~4.7 GB |
| **RAM necesaria** | ~8 GB (mínimo), 16 GB recomendado |
| **Licencia** | Llama 3.1 Community License |
| **Fortalezas** | Buen equilibrio calidad/velocidad, contexto largo, multilingüe |
| **Debilidades** | Inferior a phi4 en razonamiento puro |
| **Uso en el RAG** | Alternativa equilibrada si phi4 es demasiado lento |

```bash
ollama pull llama3.1:8b
```

### 3.4 gemma2:2b (Chat — Ultra ligero y rápido)

| Campo | Detalle |
|---|---|
| **Propósito** | Modelo de chat / generación de texto |
| **Desarrollador** | Google DeepMind |
| **Parámetros** | 2B |
| **Contexto máximo** | 8.192 tokens |
| **Cuantización** | Q4_K_M |
| **Tamaño en disco** | ~1.6 GB |
| **RAM necesaria** | ~4 GB |
| **Licencia** | Gemma Terms of Use |
| **Fortalezas** | Extremadamente rápido, funciona en hardware muy modesto |
| **Debilidades** | Calidad inferior, puede alucinar más, español limitado |
| **Uso en el RAG** | Demo rápida de velocidad / hardware mínimo |

```bash
ollama pull gemma2:2b
```

### Comparativa rápida de modelos

| Modelo | Parámetros | RAM mín. | Disco | Velocidad* | Calidad RAG | Español |
|---|---|---|---|---|---|---|
| gemma2:2b | 2B | 4 GB | 1.6 GB | ★★★★★ | ★★☆☆☆ | Regular |
| llama3.1:8b | 8B | 8 GB | 4.7 GB | ★★★★☆ | ★★★☆☆ | Bueno |
| phi4:14b | 14B | 16 GB | 9.1 GB | ★★★☆☆ | ★★★★☆ | Aceptable |
| gpt-4o (OpenAI) | N/A | N/A | N/A | ★★★★★ | ★★★★★ | Excelente |

*Velocidad percibida en M3 Pro 18 GB para los modelos locales.

---

## 4. ChromaDB

| Campo | Detalle |
|---|---|
| **Qué es** | Base de datos vectorial open source |
| **Licencia** | Apache 2.0 |
| **Persistencia** | En disco (SQLite + HNSW index) |
| **Puerto por defecto** | 8000 (configurable) |
| **Web** | https://www.trychroma.com |
| **Docs** | https://docs.trychroma.com |

### Instalación y arranque

```bash
# Instalar (dentro del entorno virtual de Python)
pip install chromadb

# Arrancar como servidor apuntando a una base existente
chroma run --path ./chroma_guias_clinicas --port 8000

# Arrancar otra instancia (Ollama) en otro puerto
chroma run --path ./chroma_guias_ollama --port 8001

# Verificar que está corriendo
curl http://localhost:8000/api/v2/heartbeat
```

### Dos instancias en la demo

| Instancia | Puerto | Embeddings utilizados | Dimensiones | Collection |
|---|---|---|---|---|
| OpenAI | 8000 | text-embedding-3-small | 1.536 | guias_clinicas |
| Ollama | 8001 | nomic-embed-text | 768 | guias_clinicas_ollama |

**Regla crítica:** Las dimensiones de los embeddings deben coincidir entre indexación y consulta. No se puede indexar con nomic-embed-text (768 dim) y consultar con text-embedding-3-small (1.536 dim), ni viceversa. ChromaDB rechaza la query con error de dimensiones.

---

## 5. Python (scripts de indexación)

| Campo | Detalle |
|---|---|
| **Versión** | Python 3.9+ |
| **Entorno virtual** | ~/flowise-rag |

### Setup del entorno

```bash
# Crear entorno virtual
python3 -m venv ~/flowise-rag

# Activar
source ~/flowise-rag/bin/activate

# Instalar dependencias
pip install chromadb langchain langchain-openai langchain-chroma \
            langchain-community langchain-text-splitters pypdf

# Desactivar cuando se termine
deactivate
```

### Dependencias Python utilizadas

| Paquete | Propósito |
|---|---|
| chromadb | Cliente de ChromaDB |
| langchain | Framework de orquestación LLM |
| langchain-openai | Integración OpenAI (embeddings + chat) |
| langchain-chroma | Integración ChromaDB con LangChain |
| langchain-community | Integraciones comunitarias (Ollama, PyPDF, etc.) |
| langchain-text-splitters | Splitters de texto (RecursiveCharacterTextSplitter) |
| pypdf | Lector de PDFs |

### Scripts creados

**indexar_pdfs.py** — Indexa PDFs con OpenAI Embeddings
- Itera archivo por archivo en la carpeta
- Batches de 50 chunks (evita límite de 300K tokens/request de OpenAI)
- Guarda en ChromaDB persistente en `./chroma_guias_clinicas`

**indexar_pdfs_ollama.py** — Indexa PDFs con Ollama Embeddings
- Mismo flujo pero usando nomic-embed-text local
- Batches de 25 chunks
- Guarda en ChromaDB persistente en `./chroma_guias_ollama`
- Sin límites de API, sin coste, sin envío de datos

### Ejecución

```bash
source ~/flowise-rag/bin/activate

# Con OpenAI
export OPENAI_API_KEY="sk-..."
python indexar_pdfs.py

# Con Ollama (debe estar corriendo)
python indexar_pdfs_ollama.py
```

---

## 6. OpenAI API (variante cloud)

| Campo | Detalle |
|---|---|
| **Modelos usados** | gpt-4o (chat), text-embedding-3-small (embeddings) |
| **Dimensiones embeddings** | 1.536 |
| **Free tier** | No (requiere cuenta con crédito) |
| **Pricing gpt-4o** | $2.50/M input tokens, $10/M output tokens |
| **Pricing embeddings** | $0.02/M tokens |
| **Coste estimado demo** | ~$0.20-0.50 (indexación + 20 consultas) |
| **Web** | https://platform.openai.com |

---

## 7. Webapp demo (HTML)

| Campo | Detalle |
|---|---|
| **Archivo** | nexora_health_v2.html |
| **Tecnología** | HTML + CSS + JavaScript vanilla |
| **Dependencias externas** | Google Fonts (DM Sans, Playfair Display), Flowise Embed CDN |
| **Funcionalidad** | Chat central vía API REST de Flowise + switch Ollama/OpenAI |
| **Requisitos** | Flowise corriendo en localhost:3000 |

### Configuración

Editar dos Chatflow IDs en el bloque `CONFIG` del JavaScript:

```javascript
const CONFIG = {
    ollama: {
        chatflowId: 'ID-DEL-CHATFLOW-OLLAMA',
    },
    openai: {
        chatflowId: 'ID-DEL-CHATFLOW-OPENAI',
    },
};
```

Los IDs se obtienen en Flowise → abrir chatflow → botón "API Endpoint" (arriba a la derecha).

---

## 8. Requisitos de hardware

### Mínimos para la demo completa (ambas variantes)

| Recurso | Mínimo | Recomendado |
|---|---|---|
| RAM | 16 GB | 18+ GB |
| Disco libre | 15 GB | 25 GB |
| CPU | Apple M1 / Intel i5 10gen+ | Apple M3 Pro / AMD Ryzen 7 |
| GPU | No necesaria (Apple Silicon usa Metal automáticamente) | — |
| Internet | Solo para descargas iniciales y variante OpenAI | — |

### Solo variante local (Ollama)

| Recurso | Con gemma2:2b | Con phi4:14b |
|---|---|---|
| RAM | 8 GB | 16+ GB |
| Disco | 5 GB | 15 GB |

---

## 9. Puertos utilizados

| Servicio | Puerto | Comando |
|---|---|---|
| Flowise | 3000 | `npx flowise start` |
| Ollama | 11434 | Automático al abrir la app |
| ChromaDB (OpenAI) | 8000 | `chroma run --path ./chroma_guias_clinicas --port 8000` |
| ChromaDB (Ollama) | 8001 | `chroma run --path ./chroma_guias_ollama --port 8001` |

---

## 10. Checklist de arranque (todo el stack)

```bash
# 1. Ollama (verificar que está corriendo)
curl http://localhost:11434

# 2. ChromaDB instancia OpenAI
chroma run --path ./chroma_guias_clinicas --port 8000

# 3. ChromaDB instancia Ollama (en otra terminal)
chroma run --path ./chroma_guias_ollama --port 8001

# 4. Flowise
npx flowise start

# 5. Abrir webapp
open nexora_health_v2.html
```

---

*Documento generado: 16 abril 2026 · Sesión IASP S4 · UNIR*
