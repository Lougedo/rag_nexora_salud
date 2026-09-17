# RAG de NEXORA Salud en n8n + Qdrant

Montaje en la nube usado en la sesión 4 de *IA aplicada a Sectores Productivos*
(17 de septiembre de 2026). Es la versión «sin instalar nada» del RAG local con
Flowise, Ollama y ChromaDB que describe [GUIA_PIPELINE_RAG.md](GUIA_PIPELINE_RAG.md).

> ⚠️ **Prototipo docente.** NEXORA Salud es ficticia y nada de esto sirve para decisiones
> clínicas. Una prueba de concepto no es un sistema en producción: faltan control de
> acceso, límites de uso, evaluación sistemática, trazabilidad y revisión clínica.

---

## 1. Qué hay montado

```
                    ┌─────────────── INDEXAR (una vez) ───────────────┐
 GitHub (984 PDF) ─▶│ n8n 1b ─▶ n8n 1c: PDF → texto → trozos → vectores │─▶ Qdrant Cloud
                    └──────────────────────────────────────────────────┘   colección nexora_guias
                                                                            128.787 trozos
                    ┌─────────────── PREGUNTAR (cada vez) ─────────────┐        ▲
 index_n8n.html ───▶│ n8n 2: pregunta → vector → 5 trozos → redactor    │────────┘
 (navegador)    ◀───│ respuesta + fuentes (título, página, extracto)    │
                    └──────────────────────────────────────────────────┘
```

| Pieza | Qué es | Dónde |
|---|---|---|
| Orquestación | n8n Cloud | `lougedo.app.n8n.cloud`, carpeta *IASP S4 · RAG multimotor* |
| Base de datos vectorial | Qdrant Cloud, plan gratuito | Colección `nexora_guias` |
| Embeddings | OpenAI `text-embedding-3-small`, 1.536 números por trozo | Credencial propia de OpenAI |
| Redactores | OpenAI `gpt-4o-mini` y Ollama Cloud `gpt-oss:120b` | Credenciales propias |
| Troceado | 1.000 caracteres, solape de 200, una página del PDF por documento | Nodo *Recursive Character Text Splitter* |
| Interfaz | `index_n8n.html` | Este repositorio |

**Por qué Ollama no tiene embeddings propios.** Ollama Cloud solo ofrece modelos de chat.
Ollama redacta, pero busca en el mismo almacén con los vectores de OpenAI. Es la idea
central de la sesión: **el modelo que redacta se cambia cuando quieras; el de embeddings
no, porque habría que volver a indexar.**

---

## 2. Lo que hay en la base vectorial

| Capa | Contenido | Documentos |
|---|---|---|
| 1 | Guías de práctica clínica del SNS | 43 |
| 2 | Material complementario (resúmenes, borradores, traducciones) | 44 |
| 3 | Normativa y estrategia (BOE, UE, OMS, Ministerio, FDA, OCDE) | 207 |
| 4 | Documentos internos de NEXORA Salud (ficticios) | 4 |
| 5 | Artículos científicos abiertos (PLOS, Frontiers) | 686 |
| **Total** | | **984** |

- **Trozos guardados:** 128.787.
- **Sin indexar:** dos informes de la OMS (ids 206 y 210) son PDF escaneados sin capa de texto.
  Harían falta OCR.
- **Metadatos de cada trozo:** `doc_id`, `fichero`, `titulo`, `capa`, `categoria`, `fuente`
  y la página (`loc.pageNumber`). Permiten citar la fuente y, en una versión posterior,
  filtrar por capa.
- **Coste del indexado:** unos 25 millones de tokens de embeddings 🟡 (del orden de 0,50 $ con
  el precio público de septiembre de 2026). Duró unos 35 minutos, en tandas.

El detalle de las capas y de las contradicciones sembradas está en
[NEXORA_Salud_Corpus_Diseno.md](NEXORA_Salud_Corpus_Diseno.md).

---

## 3. Los flujos de n8n

| Flujo | Qué hace | Estado |
|---|---|---|
| **1 · Indexar guías** | Versión didáctica: dos extractos de las guías de diabetes en un almacén en memoria, con OpenAI y Gemini | Publicado |
| **1b · Indexar el corpus en Qdrant** | Formulario *desde / hasta* (ids del inventario). Lee `corpus_inventario.csv` y llama a 1c por cada documento | Sin publicar |
| **1c · Indexar un documento (subflujo)** | Descarga el PDF de GitHub, lo trocea, calcula los vectores y los guarda en Qdrant. Devuelve solo el número de trozos | Sin publicar |
| **2 · Preguntar a las guías** | El chat que usa la web. Prefijos `/openai` y `/ollama` (por defecto, OpenAI). Devuelve la respuesta y las fuentes | **Publicado** |
| **3 · Comparar motores** | Formulario: la misma pregunta a OpenAI y a Ollama, con la tabla de trozos recuperados y los segundos | Sin publicar |
| **4 · Laboratorio de embeddings** | Formulario: puntuaciones de parecido entre frases con OpenAI y Gemini | Sin publicar |

### Reglas del asistente (mensaje de sistema)

1. Buscar siempre con la herramienta antes de responder.
2. Responder solo con lo que devuelva la herramienta.
3. Si no aparece: «No encuentro esa información en los documentos cargados».
4. Citar el documento (título y año).
5. Señalar cuando dos fuentes dicen cosas distintas.
6. No dar consejo médico personal.
7. Como máximo dos búsquedas por pregunta. Sin este límite, Ollama llegaba a hacer diez
   búsquedas y la petición fallaba.

---

## 4. Preguntas de prueba y resultados

Probadas el 17-sep-2026 con OpenAI sobre el corpus completo, salvo que se indique lo contrario.

| Pregunta | Qué pasó | Qué enseña |
|---|---|---|
| ¿Cuál es el objetivo de hemoglobina glicada en la diabetes tipo 1? | Da el 6,1–6,9 % de la GPC 659 (2026), pero **no menciona** el protocolo interno de 2024, que dice otra cifra | Recuperar bien no es lo mismo que detectar contradicciones |
| ¿Cuándo empieza a aplicarse el AI Act a los productos sanitarios con IA? | Recupera 9 trozos de normativa, ninguno con la fecha, y responde que no lo encuentra | Fallo de **recuperación**, no del modelo |
| ¿Qué exige NEXORA Salud antes de activar un modelo predictivo? | OpenAI y Ollama encuentran el procedimiento PRC-IA-003 y resumen fases y umbrales | Encuentra un documento de 2 páginas entre 984 |
| ¿Se puede usar la guía de diabetes tipo 2 del SNS como referencia? | 🔴 Sin probar con el corpus completo | Política interna de vigencia frente a guía de 2008 |
| ¿Cuál es el tratamiento de la migraña? | 🔴 Sin probar con el corpus completo. Con los dos extractos, ambos redactores dijeron que no lo encontraban | No inventar |

Con los extractos del principio también apareció una **invención**: Ollama añadió
«equivalente a < 7 %» a una cifra que la guía no expresa así.

---

## 5. Cómo se usa

### Abrir la interfaz

- **En local:** doble clic en `index_n8n.html`.
- **Publicada:** con GitHub Pages activado, en
  `https://lougedo.github.io/rag_nexora_salud/index_n8n.html`.

La página llama directamente al chat publicado del flujo 2. Si el flujo se despublica,
la web muestra un aviso y deja de responder.

### Volver a indexar

**Cada ejecución añade trozos nuevos con identificadores aleatorios.** Indexar dos veces el
mismo documento lo duplica. Para rehacerlo todo:

1. Vaciar o borrar la colección `nexora_guias` desde el panel de Qdrant.
2. Abrir el flujo 1b y ejecutar el formulario por tandas de 150–250 documentos
   (1–150, 151–300, 301–500, 501–750, 751–987). Cada tanda tarda unos 5 minutos.

### Añadir otro redactor

Copiar la rama de OpenAI en el flujo 2, cambiar solo el modelo de chat, dejar la
herramienta de Qdrant con **los mismos embeddings** y añadir el prefijo en *Leer el motor*.

---

## 6. Seguridad y costes

- **El chat publicado no tiene contraseña.** Su dirección está en el código de
  `index_n8n.html`. Quien la tenga puede hacer preguntas y consumir los créditos de
  OpenAI, Ollama Cloud y las ejecuciones de n8n.
- **Medidas mínimas mientras esté abierto:**
  - límite de gasto mensual en la cuenta de OpenAI;
  - despublicar el flujo 2 cuando no se use;
  - opcional: restringir *Allowed Origins* del disparador de chat al dominio de GitHub Pages.
    Solo frena a otros navegadores, no a peticiones directas.
- **No hay claves en el repositorio.** Las credenciales viven en n8n.
- **Límites de los planes gratuitos:** Qdrant Cloud (espacio del clúster) y las ejecuciones
  del plan de n8n. 🔴 No verificados para uso simultáneo de un grupo entero.

---

## 7. Problemas encontrados al montarlo

| Síntoma | Causa | Solución |
|---|---|---|
| Los embeddings de Gemini dan 404 al buscar | Las credenciales gestionadas de n8n no sirven para ese modelo | Clave propia de Google AI Studio |
| Gemini devuelve vectores vacíos sin error | Límite por minuto del plan gratuito | Pausas entre documentos; en el corpus completo, solo OpenAI |
| El lector de PDF no genera trozos | GitHub sirve los PDF como `octet-stream` | Nodo que marca el fichero como `application/pdf` |
| El PDF «desaparece» | Los nodos *Set* descartan el binario | `includeOtherFields` activado y `stripBinary` desactivado |
| Qdrant: «Not existing vector name» | Configuración de colección propia | Dejar que n8n cree la colección con sus valores |
| n8n cae al indexar 13 guías seguidas | Memoria: todos los PDF y trozos en una sola ejecución | Un subflujo por documento (1c) |
| Error 500 con Ollama | El agente superaba el máximo de iteraciones | Regla 7 y salida de error controlada |

---

## Fuentes utilizadas

- Ejecuciones de n8n del 16 y 17 de septiembre de 2026 (recuentos de trozos y respuestas).
- `corpus_inventario.csv`, `docs/estadisticas_corpus.json` y
  `docs/NEXORA_Salud_Corpus_Diseno.md` de este repositorio.

## Pendientes de validar

- 🟡 Coste real del indexado en la factura de OpenAI.
- 🔴 Espacio ocupado en Qdrant y margen del plan gratuito.
- 🔴 Comportamiento con muchos usuarios a la vez (cuotas de n8n, OpenAI y Ollama Cloud).
- 🔴 Dos preguntas de prueba sin repetir sobre el corpus completo (sección 4).
