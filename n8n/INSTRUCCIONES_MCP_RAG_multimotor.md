# Encargo: montar en n8n un RAG multimotor sobre guías clínicas (vía MCP)

> **Para la instancia de Claude que lo reciba.** Este documento es un encargo completo. Léelo
> entero antes de tocar nada. Tienes acceso al **servidor MCP de n8n** de Lou. Trabaja por
> fases y **para a pedir confirmación donde se indica**.

---

## 0 · Contexto

Lou es profesor de la asignatura *IA aplicada a Sectores Productivos* (UNIR). Sus alumnos
tienen perfil de negocio: ADE, Derecho, Economía. **No programan.** El jueves 17 de
septiembre de 2026 tienen una sesión de IA en salud con un práctico de RAG.

El objetivo no es tener un chatbot bonito. Es que los alumnos **entiendan cómo funciona un
RAG por dentro**:

- qué es trocear un documento,
- qué es un embedding y por qué **el modelo de embeddings no se puede cambiar sin volver a
  indexar**,
- que **el modelo que redacta sí se puede cambiar** libremente,
- y dónde falla: mezcla de fuentes, fuentes caducadas e invenciones.

Por eso el montaje tiene que ser **multimotor**: el mismo RAG con OpenAI, con Gemini y con
**Ollama Cloud** (Lou tiene suscripción), intercambiables, y con un flujo que enseñe los
embeddings.

**Todo lo que se vea en pantalla (nombres de nodos, notas adhesivas, formularios, mensajes)
va en español**, en lenguaje llano y sin jerga innecesaria.

---

## 1 · Reglas de trabajo

1. **Antes de escribir código de un flujo**, llama a `get_workflow_sdk_reference`. Para cada
   nodo, llama a `search_nodes` y después a `get_node_types` con sus discriminadores. **No
   adivines nombres de parámetros.**
2. **Valida cada flujo** con `validate_workflow` antes de `create_workflow_from_code`.
3. **No actives ni publiques ningún flujo** (`publish_workflow`) sin que Lou lo pida.
4. **Credenciales:**
   - Consulta `list_credentials` y `list_n8n_gateway_services`.
   - Para OpenAI y Gemini, **usa las credenciales gestionadas por n8n (gateway)** si están
     disponibles.
   - Si no lo están, o para Ollama, **no pidas claves en el chat**. Dile a Lou qué credencial
     tiene que crear en la interfaz de n8n (*Credentials → Create*) y espera.
5. **Proyecto y carpeta:** pregunta a Lou en qué proyecto crear los flujos. Si no dice
   nada, crea una carpeta `IASP S4 · RAG multimotor` en su proyecto personal y mete ahí los
   cuatro.
6. **Si un nodo o un modelo no existe** con el nombre que da este documento, elige el
   equivalente más cercano que devuelva `get_node_types` y **díselo a Lou al final**.
7. Al terminar cada fase, **resume en tres líneas** qué has creado (nombre, ID, estado) y qué
   falta.

---

## 2 · La idea clave del diseño: dos papeles que se eligen por separado

Un RAG usa dos modelos con papeles distintos, y el montaje los separa a propósito:

**A · El modelo de embeddings** convierte texto en vectores. Hay **dos**, y cada uno tiene
su propio almacén:

| Embeddings | Modelo | Dimensiones | Almacén (memory key) |
|---|---|---|---|
| `openai` | `text-embedding-3-small` | 1.536 | `guias_openai` |
| `gemini` | `models/gemini-embedding-001` | 3.072 | `guias_gemini` |

**B · El modelo que redacta** escribe la respuesta. Hay **tres**:

| Redactor | Modelo | Almacén que consulta por defecto |
|---|---|---|
| `openai` | `gpt-4o-mini` (o el mini más reciente disponible) | `guias_openai` |
| `gemini` | `models/gemini-2.5-flash` (o el Flash más reciente) | `guias_gemini` |
| `ollama` | Un modelo de **Ollama Cloud** con herramientas: `gpt-oss:120b` o, si no está, `qwen3.5` o `gemma4` | `guias_gemini`, configurable |

**Por qué Ollama no tiene fila en la tabla A:** Ollama Cloud **no ofrece modelos de
embeddings**, solo de chat. Comprobado en su catálogo (septiembre de 2026): el filtro «cloud
+ embedding» no devuelve nada. Así que el redactor de Ollama **usa los embeddings y el
almacén de otro proveedor**. Esto es justo lo que se quiere enseñar:

> **El que redacta se puede cambiar cuando quieras, incluso a otro proveedor. El de
> embeddings, no: si lo cambias, hay que volver a indexar.** Los vectores de OpenAI no se
> pueden consultar con embeddings de Gemini: son mapas distintos, con coordenadas
> distintas.

Consecuencia práctica, para la regla de cada rama: **el nodo de búsqueda usa exactamente el
mismo modelo de embeddings que se usó al indexar el almacén que consulta.** Para la rama de
Ollama, los embeddings de Gemini (o los de OpenAI, si se cambia su almacén).

**Almacén:** usa el nodo **Simple Vector Store** (`@n8n/n8n-nodes-langchain.vectorStoreInMemory`).
Guarda en la memoria de la instancia, es compartido entre flujos por *memory key* y se
borra si n8n se reinicia. Es lo que se quiere para clase: no hace falta ninguna base de
datos externa.

**Ollama Cloud en n8n:**

- Credencial de tipo **Ollama** (`ollamaApi`) con **Base URL `https://ollama.com`** y la
  **API Key** que Lou crea en <https://ollama.com/settings/keys>. La prueba de la credencial
  llama a `/api/tags`: si pasa, la conexión funciona. **La crea Lou en la interfaz.** Tú no
  pides la clave.
- Usa el nodo **Ollama Chat Model** (`lmChatOllama`). **Elige el modelo de la lista que
  devuelve la credencial**, no lo escribas a ciegas: en la API directa los nombres pueden no
  llevar el sufijo `-cloud` que se usa en local. 🟡 Compruébalo.
- El modelo **tiene que admitir herramientas** para funcionar dentro de un agente. En el
  catálogo de Ollama Cloud la mayoría las admite (gpt-oss, qwen3.5, gemma4, deepseek, glm,
  kimi…).
- Ollama Cloud tiene límites de uso según el plan. Si aparece un error de cuota, díselo a
  Lou.

**Añadir un redactor más** (Mistral, Anthropic…) es copiar una rama y cambiar el modelo de
chat. **Añadir unos embeddings más** (Cohere, por ejemplo) es copiar una rama del flujo 1,
cambiar el modelo y poner una memory key nueva. Deja una nota adhesiva en cada flujo que lo
explique.

---

## 3 · Los documentos

Dos guías de práctica clínica del Sistema Nacional de Salud, **recortadas** para que se
indexen en un minuto:

| Fichero | Año | Páginas | Objetivo de hemoglobina glicada (HbA1c) |
|---|---|---|---|
| `GPC_Diabetes_tipo_2_2008_extracto.pdf` | 2008. Su portada dice: *«Han transcurrido más de 5 años desde la publicación de esta Guía de Práctica Clínica y está pendiente su actualización»* | 30 | **Menos del 7%** |
| `GPC_Diabetes_tipo_1_2026_extracto.pdf` | 2026 | 26 | **Entre el 6,1% y el 6,9%**, o incluso menos del 6,1% |

La guía de tipo 2 dice también que **la metformina es el fármaco de elección** en personas
con sobrepeso u obesidad.

**Cómo llegan a n8n:**

- Por el formulario del flujo 1 (Lou los sube a mano), y además
- **desde URL**, para poder indexar sin intervención (y para que tú puedas probarlo con
  `execute_workflow`). Lou va a publicarlos en GitHub. **Pregúntale las URL raw** antes de la
  fase 2. Formato previsible:
  `https://raw.githubusercontent.com/Lougedo/rag_nexora_salud/main/clase_s4/<fichero>.pdf`

---

## 4 · Los cuatro flujos

### Flujo 1 · `IASP S4 · 1 · Indexar guías`

**Qué enseña:** la fase de preparación. PDF → texto → trozos → vectores → almacén, y que
cada modelo de embeddings guarda sus propios vectores.

**Dos disparadores:**

1. **Formulario** (`formTrigger`) con estos campos:
   - `Guía (PDF)`: fichero, `.pdf`, obligatorio.
   - `Embeddings`: desplegable con `Los dos`, `OpenAI` y `Gemini`. Por defecto, `Los dos`.
   - `Tamaño de trozo (caracteres)`: número, por defecto `1000`.
   - `Solapamiento (caracteres)`: número, por defecto `200`.
   - `Vaciar el almacén antes de indexar`: desplegable `No` / `Sí`. Por defecto, `No`.
2. **Manual** («Indexar las dos guías desde URL»): un nodo Set con los mismos campos (embeddings
   `Los dos`, 1000, 200, vaciar `Sí` para el primer fichero y `No` para el segundo), seguido de
   una HTTP Request que descarga cada PDF como binario. Tiene que acabar en el mismo punto que
   el formulario, con el binario en la misma propiedad. (Aquí el campo `Embeddings` va a
   `Los dos`.)

**Después:**

- Un nodo **Switch** («¿Con qué embeddings?») con dos salidas: `openai` y `gemini`. Si el
  valor es `Los dos`, el elemento tiene que ir **a las dos salidas**. Usa la opción de enviar
  a todas las salidas que coincidan, o el patrón que indique la referencia del SDK.
- **Una rama por modelo de embeddings**, idénticas salvo en el modelo:
  - Simple Vector Store en modo `insert`, con la memory key del motor y `clearStore`
    ligado al campo «Vaciar».
  - Default Data Loader en modo binario.
  - Recursive Character Text Splitter con `chunkSize` y `chunkOverlap` **tomados de los
    campos del formulario** (expresión).
  - El nodo de embeddings del motor.
  - Nombres de nodo: `OpenAI · Guardar vectores`, `OpenAI · Embeddings (1.536 números)`,
    `OpenAI · Trocear`, `OpenAI · Leer PDF`, y lo mismo para Gemini (`Gemini · Embeddings
    (3.072 números)`…).
- **Resumen final:** que la última página del formulario, o la salida del flujo manual,
  diga cuántos trozos ha guardado cada motor, con qué tamaño y con qué solapamiento. Por
  ejemplo: «Gemini: 164 trozos de 1.000 caracteres (solape 200) guardados en guias_gemini».

**Notas adhesivas (en el lienzo, en español):**

- Arriba: «**Fase 1 · Preparar.** Se hace una vez por documento. El PDF se convierte en
  texto, se corta en trozos y cada trozo se convierte en una lista de números (su
  *embedding*).»
- Junto al Switch: «**Cada modelo de embeddings tiene su propio almacén.** Los números de OpenAI no se
  entienden con los de Gemini: son mapas distintos. Si cambias el modelo de embeddings, hay
  que volver a indexar.»
- Junto al troceador: «**El tamaño del trozo es lo que más influye en la calidad.** Prueba
  con 150 y con 3000 y compara las respuestas.»
- «**¿Y Ollama?** Ollama Cloud no ofrece modelos de embeddings, solo de chat. Por eso aquí
  no aparece: en el flujo 2, Ollama redacta usando los vectores de Gemini.»
- Una nota «**Añadir otros embeddings**» con los cambios.

---

### Flujo 2 · `IASP S4 · 2 · Preguntar a las guías`

**Qué enseña:** la fase de consulta, y que **el modelo que redacta se puede cambiar**
(incluso a otro proveedor), pero el buscador tiene que usar los embeddings de su almacén.

**Disparador:** Chat Trigger en modo chat alojado, con mensaje de bienvenida:

> Pregúntame sobre las guías de diabetes. Para elegir quién redacta, empieza tu mensaje
> con /openai, /gemini o /ollama. Sin nada, uso el redactor por defecto.

**Después:**

1. Nodo Set **«Configuración»**, fácil de cambiar en clase, con:
   - `redactor_por_defecto = gemini`
   - `almacen_para_ollama = gemini` (el almacén, y por tanto los embeddings, que usa la rama de
     Ollama)
2. Nodo Code o Set **«Leer el motor»** que:
   - detecta un prefijo `/openai`, `/gemini` u `/ollama` al principio del mensaje,
   - lo quita del texto,
   - y devuelve `motor` y `pregunta`.
3. **Switch** por `motor` → tres ramas.
4. **Cada rama tiene su propio AI Agent** (`@n8n/n8n-nodes-langchain.agent`):
   - el texto de entrada es la `pregunta` limpia, y la sesión de memoria la del chat;
   - modelo de chat del redactor (en la rama de Ollama, el Ollama Chat Model con la
     credencial de Ollama Cloud);
   - memoria de ventana (la misma `sessionId` del chat);
   - **herramienta**: Simple Vector Store en modo `retrieve-as-tool`, con la memory key del
     motor, `topK = 4`, metadatos incluidos, nombre de herramienta `guias_clinicas` y la
     descripción de abajo;
   - **los embeddings de la herramienta son los mismos que los del almacén que consulta**.
     OpenAI → `guias_openai` + embeddings de OpenAI. Gemini → `guias_gemini` + embeddings de
     Gemini. Ollama → el almacén de `almacen_para_ollama`, con **sus** embeddings. Como un
     sub-nodo de embeddings no se puede cambiar por expresión, la rama de Ollama puede
     llevar **dos sub-ramas** (con almacén de Gemini o de OpenAI) tras un Switch sobre
     `almacen_para_ollama`, o solo la de Gemini si eso complica demasiado. Díselo a Lou;
   - mensaje de sistema: el de abajo, con una línea final que diga qué motor responde.
5. **Salida:** cada rama termina en un nodo que deja la respuesta en `{ output: "..." }`,
   con el prefijo del motor. Por ejemplo: «[Gemini] El objetivo es…». Configura el Chat
   Trigger para que responda con el último nodo, o con streaming si la referencia lo
   recomienda y funciona con ramas.

**Mensaje de sistema** (idéntico en las tres ramas):

```
Eres un asistente que responde preguntas sobre guías de práctica clínica del Sistema Nacional de Salud.

Reglas:
1. Antes de responder, usa SIEMPRE la herramienta guias_clinicas.
2. Responde solo con lo que devuelva la herramienta. No uses tu conocimiento general.
3. Si la información no aparece, responde exactamente: "No encuentro esa información en las guías cargadas."
4. Di de qué guía sale cada dato (tipo 1 o tipo 2, y su año si aparece).
5. No des consejo médico personal. Responde en español.
```

**Descripción de la herramienta:**

```
Busca fragmentos de texto en las guías de práctica clínica cargadas (diabetes tipo 1 y diabetes tipo 2). Úsala para cualquier pregunta clínica.
```

**Notas adhesivas:**

- «**Fase 2 · Preguntar.** Tu pregunta se convierte en números con el MISMO modelo que se
  usó al indexar, se buscan los 4 trozos más parecidos y el modelo redacta con ellos.»
- «**Mira dentro:** abre *Logs* → *guias_clinicas* para ver qué trozos ha recuperado.»
- Junto a la rama de Ollama: «**Ollama redacta, pero busca con los vectores de Gemini.**
  Quien redacta y quien convierte en números pueden ser de empresas distintas.»
- «**Experimento:** cambia en una rama los embeddings de la herramienta por los del otro
  proveedor y pregunta. Verás un error de dimensiones (1.536 frente a 3.072), o respuestas
  sin sentido. Esa es la lección.»

---

### Flujo 3 · `IASP S4 · 3 · Comparar motores`

**Qué enseña:** la misma pregunta, los mismos documentos y tres motores. ¿Recuperan los
mismos trozos? ¿Responden lo mismo? ¿Cuánto tardan?

**Disparador:** formulario con un campo `Pregunta` (texto largo) y un campo `Trozos a
recuperar (top-K)`, numérico, por defecto 4.

**Después:**

- Tres ramas **en paralelo**, una por redactor, con la misma configuración que el flujo 2
  (su agente, su modelo, su herramienta, sus embeddings y su memory key). La de Ollama
  consulta `guias_gemini`. `topK` sale del formulario.
- En cada agente, activa la opción de **devolver los pasos intermedios**, para poder enseñar
  qué trozos recuperó la herramienta.
- Mide el tiempo de cada rama: marca de tiempo antes y después, en un Set o un Code.
- **Merge** que espere a las tres ramas.
- **Code «Montar la comparación»** que construya una tabla en HTML con:
  - redactor y almacén (por ejemplo, «Ollama · vectores de Gemini»);
  - respuesta;
  - trozos recuperados, con un extracto de unos 120 caracteres y fichero y página si
    vienen en los metadatos;
  - segundos.
- **Página final del formulario** que muestre esa tabla.
- Si una rama falla (cuota, credencial), la tabla lo dice en su fila («Ollama: error de
  cuota») y el flujo no se rompe. Activa «continuar si hay error» en los agentes y diseña el
  Merge para que no se quede esperando. Explica tu solución a Lou.

**Nota adhesiva:** «**Compara dos cosas.** OpenAI y Gemini buscan con mapas de significado
distintos, y por eso no siempre recuperan los mismos trozos. Gemini y Ollama usan el mismo
mapa: recuperan los mismos trozos y solo cambia cómo redactan.»

---

### Flujo 4 · `IASP S4 · 4 · Laboratorio de embeddings`

**Qué enseña:** qué es un embedding y qué significa «estar cerca», sin documentos
largos de por medio.

**Disparador:** formulario con:

- `Frase de búsqueda`, por defecto: `Paciente con dolor torácico agudo`.
- `Frases a comparar`, texto largo, una por línea, por defecto:
  ```
  Episodio de angina severa
  Manejo del ataque cardiaco
  Chest pain in an adult patient
  Objetivo de hemoglobina glicada
  Receta de tortilla española
  ```

**Después, por cada modelo de embeddings (OpenAI y Gemini):**

1. Code «Frases a documentos»: una línea, un elemento.
2. Simple Vector Store en modo `insert` con memory key `lab_<motor>` y **`clearStore =
   true`**, más su Default Data Loader (modo JSON), un splitter con un trozo grande (para que
   cada frase sea un solo trozo) y los embeddings del motor.
3. Simple Vector Store en modo `load` («Get Many») con la misma memory key, la `Frase de
   búsqueda` como consulta, `topK` igual al número de frases y los embeddings del motor.
   Devuelve cada frase con su **puntuación de similitud**.

Y al final:

- **Merge** de las dos ramas y **Code «Tabla de parecidos»**: una fila por frase, una columna
  por modelo con la puntuación redondeada a 3 decimales, ordenadas por la media.
- **Página final** con la tabla y este texto:

  > Cuanto más alta la puntuación, más cerca en significado. Fíjate en que «Manejo del
  > ataque cardiaco» sale cerca aunque no comparte ninguna palabra con la búsqueda, y en que
  > la frase en inglés también. La tortilla, lejos. Y fíjate en que **cada modelo da números
  > distintos**: por eso no se pueden mezclar.

**Opcional: el vector «en crudo».** Si hay credencial propia de OpenAI (no la gestionada
por n8n), una HTTP Request a `https://api.openai.com/v1/embeddings` con la frase de
búsqueda, y un Code que muestre **la dimensión del vector y sus 8 primeros números**. Si
solo hay credenciales gestionadas, sáltalo y díselo a Lou. **Pregúntale antes de añadirlo.**

**Nota adhesiva:** «**Un embedding es una lista de números que representa el significado de
un texto.** Dos textos parecidos tienen listas parecidas. La «puntuación» mide cuánto se
parecen, de 0 (nada) a 1 (lo mismo).»

---

## 5 · Fases y pruebas

### Fase 1 · Planificar (sin crear nada)

- Llama a `get_workflow_sdk_reference`, `get_workflow_best_practices` (`chatbot`,
  `form_input`, `document_processing`), `search_nodes` y `get_node_types` para todos los
  nodos.
- Comprueba credenciales y servicios gestionados.
- **Entrega a Lou un plan corto:** los nodos exactos de cada flujo, las credenciales que vas
  a usar, el modelo de Ollama Cloud que has elegido de la lista y las URL que necesitas.
  **Espera su OK.**

### Fase 2 · Construir

Por este orden: flujo 1, flujo 2, flujo 4 y flujo 3. Valida cada uno y créalo sin activarlo.

Para cada flujo, usa `prepare_workflow_pin_data` y `test_workflow` para comprobar la
estructura, y di qué nodos quedan simulados en esa prueba.

### Fase 3 · Probar de verdad

Con credenciales disponibles y las URL de los PDF:

1. Ejecuta el flujo 1 por el disparador manual (`execute_workflow`). Anota cuántos trozos
   guarda cada motor.
2. Ejecuta el flujo 4 con los valores por defecto. Anota la tabla.
3. Si puedes ejecutar los flujos 2 y 3 de forma no interactiva, hazlo con las preguntas de
   abajo. Si no, pásale a Lou las preguntas para que las haga él en el chat y el formulario.

| # | Pregunta | Resultado esperado |
|---|---|---|
| 1 | ¿Qué cifra de hemoglobina glicada se recomienda como objetivo en la diabetes tipo 1? | Entre el 6,1% y el 6,9% (o menos), según la guía de 2026 |
| 2 | ¿Cuál es el objetivo de hemoglobina glicada? | **Debería distinguir** tipo 1 y tipo 2 (<7%). Si da una sola cifra sin decir de qué guía, es el fallo que se quiere enseñar |
| 3 | ¿Cuál es el fármaco de elección en diabetes tipo 2 con sobrepeso? | Metformina, guía de 2008 |
| 4 | ¿Cuál es el tratamiento de la migraña? | «No encuentro esa información en las guías cargadas.» |
| 5 | ¿Está vigente la guía de diabetes tipo 2? | Depende de si recupera el trozo con el aviso de la portada. Anota lo que pase |

**Entrega:** una tabla por redactor con lo que respondió a cada pregunta y cuántos trozos
recuperó, y cualquier diferencia llamativa. Sobre todo: ¿Gemini y Ollama, que comparten
trozos, responden distinto? Es material para la clase.

### Fase 4 · Entregar

- La lista de flujos creados, con nombre, ID, proyecto y carpeta.
- Las credenciales usadas, y las que falten.
- Cualquier nodo o modelo que hayas sustituido.
- **Qué tiene que hacer Lou en la interfaz**: crear la credencial de Ollama Cloud, abrir la
  URL del formulario…
- Si puedes, el JSON de cada flujo (`get_workflow_details`), para guardarlo en
  `Flowise/rag_nexora_salud/n8n/`.

---

## 6 · Problemas previsibles

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| Error de dimensiones al buscar | Los embeddings de la búsqueda no son los del indexado | Mismo modelo en las dos puntas de cada rama |
| El agente responde sin buscar | Mensaje de sistema o descripción de la herramienta flojos | Revisa la regla 1 y la descripción |
| El chat dice que no encuentra nada | El almacén está vacío (n8n reiniciado, o memory key distinta) | Reindexar; comprobar que las memory keys coinciden |
| Trozos repetidos | Se indexó dos veces sin vaciar | `Vaciar = Sí` en la primera guía |
| La credencial de Ollama no pasa la prueba | Base URL o clave mal puestas | Base URL exactamente `https://ollama.com`, sin `/api` al final; clave de ollama.com/settings/keys |
| «Model not found» en Ollama | Nombre del modelo escrito a mano | Elegirlo de la lista que carga la credencial |
| Ollama responde pero no usa la herramienta | El modelo no admite herramientas | Elegir uno con la etiqueta *tools* en el catálogo |
| Error de cuota en Ollama | Límite del plan de Ollama Cloud | Esperar, o cambiar a un modelo más pequeño |
| Error 429 | Límite de peticiones del proveedor | Bajar `batchSize` de los embeddings y reintentar |
| El Merge del flujo 3 se queda esperando | Una rama desactivada no emite nada | Ver la nota del flujo 3 |

---

## 7 · Lo que NO hay que hacer

- No usar bases de datos vectoriales externas (Pinecone, Supabase, Qdrant…). Solo el Simple
  Vector Store.
- No activar ni publicar flujos, ni programar ejecuciones.
- No pedir ni escribir claves de API en el chat.
- No añadir funcionalidades que no estén aquí (envío de correos, hojas de cálculo…). Si
  crees que algo mejora la clase, **propónlo, no lo hagas**.
- No usar documentos distintos de las dos guías.
- No intentar usar un Ollama local ni túneles: Ollama va por Ollama Cloud.
