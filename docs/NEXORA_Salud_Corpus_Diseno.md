# Corpus NEXORA Salud — Diseño y justificación

## Para qué existe

En clase, los alumnos montan un RAG con **dos guías** recortadas. Funciona, pero da una idea
falsa de la escala: dos documentos caben en cualquier chat.

Este corpus existe para enseñar la **dimensión real** con la que trabaja un RAG en una
organización sanitaria: casi mil documentos, 31.000 páginas y unos 24 millones de tokens,
de fuentes distintas, en dos idiomas, con versiones que se solapan y se contradicen.

## Qué se ha buscado

1. **Volumen suficiente para que no quepa en ninguna herramienta de uso general.** Es unas
   120 veces el contexto de un modelo de 200.000 tokens y supera el límite de fuentes de
   Gemini Notebook en todos sus planes.
2. **Fuentes reales y públicas.** Guías del SNS, legislación, estrategia del Ministerio,
   OMS, FDA y OCDE. Todas con URL de origen en el inventario.
3. **Heterogeneidad.** Clínica, normativa y documentos internos. Es lo que obliga a pensar
   en filtros, capas y agentes que eligen fuente.
4. **Ruido realista.** Resúmenes, guías rápidas, traducciones, material metodológico y
   borradores junto a la versión final. En un hospital real la documentación está así.
5. **Contradicciones a propósito.** Para que el alumno vea que el RAG no las resuelve solo.

## Las capas

| Capa | Contenido | Para qué sirve en clase |
|---|---|---|
| 1 · Guías completas | 43 guías de práctica clínica del SNS | El núcleo: preguntas clínicas con respuesta citable |
| 2 · Complementario | 44 resúmenes, herramientas, revisiones, borradores y traducciones | Ruido y duplicados; filtrar por metadatos |
| 3 · Normativa y estrategia | 207 textos: UE, 65 del BOE, Ministerio, 110 de la OMS, FDA y OCDE | Preguntas regulatorias; mezcla con la parte clínica |
| 4 · Interno (ficticio) | 4 documentos de NEXORA Salud | Reglas propias que chocan con las fuentes externas |
| 5 · Literatura abierta | 686 artículos CC BY de PLOS y Frontiers | Volumen, inglés, y preguntas cuya respuesta está repartida entre muchos artículos |

## Las contradicciones, una a una

| Situación | Documentos | Qué debería hacer un buen sistema |
|---|---|---|
| Guía antigua frente a guía nueva | GPC 429 (diabetes tipo 2, 2008) y GPC 659 (diabetes tipo 1, 2026) | Distinguir el tipo de diabetes y avisar de la antigüedad |
| Guía caducada | GPC 575 (depresión en la infancia) | Avisar de su estado |
| Borrador frente a versión final | Exposición pública de las GPC 612, 618, 625, 635, 641, 652 y 659 | No usar el borrador |
| Protocolo interno frente a guía nacional | PRT-END-014 (2024, HbA1c < 7% en tipo 1) y GPC 659 (2026, 6,1-6,9%) | Señalar la discrepancia; el protocolo tiene la revisión vencida |
| Política interna de vigencia | POL-DOC-002 prohíbe usar guías de más de 5 años sin revisión | Aplicarla a la GPC 429 |
| Validación local | PRC-IA-003 y el caso del modelo de sepsis de Epic | Explicar por qué no basta la validación del proveedor |
| Norma original frente a su modificación | AI Act (2024) y el informe del Ministerio sobre el Digital Omnibus | Dar la fecha vigente y citar la modificación |
| PDF escaneados | Dos informes de la OMS sin capa de texto | Detectarlos y pasarles OCR antes de indexar |
| Ruido de búsqueda | Normas del BOE sobre sanidad animal que entraron por la palabra «sanitario» | Filtrar por metadatos o revisar el inventario |

## Preguntas de prueba

| Pregunta | Qué se espera ver |
|---|---|
| ¿Cuál es el objetivo de hemoglobina glicada en la diabetes tipo 1? | Conflicto entre la GPC de 2026 y el protocolo interno de 2024 |
| ¿Se puede usar la guía de diabetes tipo 2 del SNS como referencia? | La política POL-DOC-002 y el aviso de la propia guía |
| ¿Cuándo empieza a aplicarse el AI Act a los productos sanitarios con IA? | Conflicto: el texto original del AI Act dice **2 de agosto de 2027**; el informe del Ministerio sobre el Digital Omnibus dice **2 de agosto de 2028**. Si el buscador solo trae el reglamento, el RAG dará la fecha antigua |
| ¿Qué exige NEXORA Salud antes de activar un modelo predictivo? | Las fases y umbrales de PRC-IA-003 |
| ¿Cuál es el tratamiento de la migraña? | «No encuentro información». No hay guía de migraña |

## Límites conocidos

- Las guías de GuíaSalud cambian: el inventario refleja el catálogo de septiembre de 2026.
- Hay documentos en inglés (OMS, FDA, OCDE y algunas traducciones). Es intencionado: los
  modelos de embeddings multilingües los recuperan igual.
- Cuatro guías ya no están en el catálogo público y se incluyen desde una copia local.
- La capa 5 está elegida por búsqueda automática: hay artículos poco relacionados con la
  asistencia sanitaria. Es parte del ruido.
- Los documentos internos son breves (6 páginas en total). Pesan poco, pero son los que más
  conflictos provocan.
