#!/usr/bin/env python3
"""
generar_corpus_nexora_salud.py
==============================
Genera los 4 documentos internos de NEXORA Salud (grupo hospitalario FICTICIO) que
completan el corpus del RAG de la asignatura IASP (UNIR).

Están escritos para provocar situaciones que un RAG no resuelve solo:

  1. Protocolo de uso de IA clínica   → reglas internas que el asistente debería citar.
  2. Política de vigencia de guías    → dice que una guía con más de 5 años no se usa sin
                                        revisión. Choca con la GPC de diabetes tipo 2 (2008).
  3. Validación local de modelos      → inspirado en el caso del modelo de sepsis de Epic.
  4. Protocolo interno de diabetes    → de 2024, dice que prevalece sobre las guías externas y
                                        fija <7% también para tipo 1, que la GPC de 2026 ya baja a
                                        6,1-6,9%. Y su revisión está vencida. Tercera fuente que se
                                        mezcla con las dos guías de diabetes.

⚠️ TODO ES FICTICIO y con fines docentes. Cada página lo indica. No usar para decisiones
clínicas.

Uso:
    pip install reportlab
    python generar_corpus_nexora_salud.py
    python generar_corpus_nexora_salud.py --output-dir ./otra_carpeta
"""
from __future__ import annotations

import argparse
from pathlib import Path

try:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (HRFlowable, PageBreak, Paragraph, SimpleDocTemplate,
                                    Spacer, Table, TableStyle)
except ImportError:
    raise SystemExit("ERROR: falta reportlab. Instala con: pip install reportlab")

AZUL = HexColor("#0b5563")
st = getSampleStyleSheet()
T = ParagraphStyle("T", parent=st["Title"], fontSize=19, textColor=AZUL, spaceAfter=6)
SUB = ParagraphStyle("S", parent=st["Normal"], fontSize=10.5, alignment=TA_CENTER,
                     textColor=HexColor("#555555"), spaceAfter=18)
H1 = ParagraphStyle("H1", parent=st["Heading1"], fontSize=13.5, textColor=AZUL,
                    spaceBefore=14, spaceAfter=6)
H2 = ParagraphStyle("H2", parent=st["Heading2"], fontSize=11.5, textColor=HexColor("#2e6da4"),
                    spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=st["Normal"], fontSize=10, leading=14, spaceAfter=6)
B = ParagraphStyle("B", parent=P, leftIndent=14, bulletIndent=4)
AVISO = "DOCUMENTO FICTICIO CON FINES DOCENTES · NEXORA SALUD NO EXISTE · NO USAR PARA DECISIONES CLÍNICAS"


def pie(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica-Oblique", 7.5)
    canvas.setFillColor(HexColor("#b00020"))
    canvas.drawCentredString(A4[0] / 2, 1.2 * cm, AVISO)
    canvas.setFillColor(HexColor("#777777"))
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm - 10, f"Página {doc.page}")
    canvas.restoreState()


def tabla(filas, anchos):
    t = Table(filas, colWidths=anchos)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#bbbbbb")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def construir(ruta: Path, titulo: str, subtitulo: str, bloques):
    doc = SimpleDocTemplate(str(ruta), pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                            topMargin=2 * cm, bottomMargin=2.2 * cm, title=titulo,
                            author="NEXORA Salud (ficticio)")
    story = [Paragraph(titulo, T), Paragraph(subtitulo, SUB),
             HRFlowable(width="100%", color=AZUL), Spacer(1, 8)]
    for tipo, contenido in bloques:
        if tipo == "h1":
            story.append(Paragraph(contenido, H1))
        elif tipo == "h2":
            story.append(Paragraph(contenido, H2))
        elif tipo == "p":
            story.append(Paragraph(contenido, P))
        elif tipo == "ul":
            story += [Paragraph(x, B, bulletText="•") for x in contenido]
        elif tipo == "tabla":
            filas, anchos = contenido
            story += [tabla(filas, anchos), Spacer(1, 8)]
        elif tipo == "salto":
            story.append(PageBreak())
    doc.build(story, onFirstPage=pie, onLaterPages=pie)


# ─────────────────────────────────────────────────────────────── documentos

def doc_protocolo_ia():
    return ("NEXORA_Salud_Protocolo_Uso_IA_Clinica_v2.1.pdf",
            "Protocolo de uso de inteligencia artificial en la práctica clínica",
            "NEXORA Salud · Código PRT-IA-001 · Versión 2.1 · Aprobado por el Comité de Dirección Médica el 12 de marzo de 2026",
            [
        ("h1", "1. Objeto y alcance"),
        ("p", "Este protocolo regula el uso de herramientas de inteligencia artificial (IA) por parte de los "
              "profesionales de los centros de NEXORA Salud. Se aplica a cualquier herramienta que genere "
              "texto, resúmenes, alertas, predicciones o propuestas diagnósticas o terapéuticas, tanto si está "
              "integrada en la historia clínica electrónica como si se accede a ella desde un navegador."),
        ("h1", "2. Principios"),
        ("ul", [
            "<b>Supervisión humana.</b> Ninguna recomendación generada por IA se aplica a un paciente sin la "
            "revisión y la firma de un profesional sanitario identificado.",
            "<b>Trazabilidad.</b> Toda respuesta usada en la atención debe poder vincularse a su fuente "
            "(guía, protocolo o documento) y a la versión vigente de esa fuente.",
            "<b>Minimización de datos.</b> No se introducen datos identificativos de pacientes en herramientas "
            "que no estén autorizadas por el Delegado de Protección de Datos.",
            "<b>Validación local.</b> Ningún modelo predictivo se activa sin superar el procedimiento "
            "PRC-IA-003 de validación con población propia.",
        ]),
        ("h1", "3. Herramientas autorizadas"),
        ("tabla", ([
            ["Herramienta", "Uso autorizado", "Datos de pacientes", "Responsable"],
            ["Asistente de guías clínicas (RAG)", "Consulta de guías y protocolos vigentes", "No", "Dirección Médica"],
            ["Transcripción de consultas", "Borrador de la nota clínica", "Sí, con consentimiento verbal", "Sistemas de Información"],
            ["Alerta de deterioro clínico", "Aviso a enfermería en planta", "Sí", "Comité de IA"],
            ["Chatbots generalistas de uso público", "Ninguno con datos clínicos", "Prohibido", "—"],
        ], [5 * cm, 4.4 * cm, 3.4 * cm, 3.6 * cm])),
        ("h1", "4. Uso del asistente de guías clínicas"),
        ("p", "El asistente responde únicamente con los documentos cargados en su base documental. Antes de "
              "aplicar una respuesta, el profesional debe comprobar:"),
        ("ul", [
            "Que la respuesta cita la guía o el protocolo del que procede.",
            "Que esa guía está <b>vigente</b> según la Política de vigencia POL-DOC-002. Una guía marcada como "
            "pendiente de actualización no es una referencia válida por sí sola.",
            "Que no existe un protocolo interno de NEXORA Salud que prevalezca sobre la guía.",
            "Que la respuesta corresponde al tipo de paciente consultado (por ejemplo, diabetes tipo 1 o tipo 2).",
        ]),
        ("p", "Si el asistente responde «No encuentro esa información en las guías cargadas», el profesional "
              "no debe reformular la pregunta hasta obtener una respuesta: debe consultar la fuente directamente."),
        ("h1", "5. Incidencias"),
        ("p", "Cualquier respuesta incorrecta, inventada o desactualizada se notifica en un plazo de 48 horas "
              "mediante el formulario INC-IA del portal interno. El Comité de IA revisa las incidencias cada mes "
              "y publica un informe trimestral con la tasa de respuestas corregidas."),
        ("h1", "6. Formación"),
        ("p", "Todo profesional que use herramientas de IA completa el curso interno «IA clínica segura» "
              "(4 horas) antes de recibir acceso, y una actualización anual de 1 hora."),
    ])


def doc_vigencia():
    return ("NEXORA_Salud_Politica_Vigencia_Guias_Clinicas.pdf",
            "Política de vigencia de guías y protocolos clínicos",
            "NEXORA Salud · Código POL-DOC-002 · Versión 1.4 · Vigente desde el 1 de enero de 2026",
            [
        ("h1", "1. Por qué existe esta política"),
        ("p", "Una guía de práctica clínica refleja la evidencia disponible en el momento en que se escribió. "
              "Con el tiempo aparecen fármacos, estudios y criterios nuevos. Un sistema que consulta guías de "
              "forma automática no distingue por sí mismo una guía actual de una desactualizada: por eso la "
              "vigencia se gestiona como un dato más de cada documento."),
        ("h1", "2. Estados de un documento"),
        ("tabla", ([
            ["Estado", "Definición", "¿Se puede usar como referencia?"],
            ["Vigente", "Publicada o revisada hace menos de 5 años", "Sí"],
            ["Pendiente de actualización", "Más de 5 años sin revisión, o marcada así por el organismo que la publica", "Solo con validación del Comité de Guías"],
            ["Borrador / exposición pública", "Versión previa a la publicación definitiva", "No"],
            ["Retirada o caducada", "Sustituida por otra o retirada por su autor", "No"],
            ["Material complementario", "Resúmenes, herramientas, infografías o versiones traducidas", "Solo junto a la guía completa vigente"],
        ], [4.2 * cm, 7.2 * cm, 5 * cm])),
        ("h1", "3. Regla de los cinco años"),
        ("p", "Una guía con más de <b>5 años</b> desde su publicación o su última revisión se considera "
              "<b>pendiente de actualización</b>, aunque siga disponible en internet. En particular, la "
              "<b>Guía de Práctica Clínica sobre Diabetes tipo 2 del SNS (2008)</b> está en este estado y su "
              "propia portada lo indica. Sus recomendaciones solo pueden aplicarse si el Comité de Guías "
              "confirma que siguen vigentes; en caso de discrepancia prevalece el protocolo interno PRT-END-014."),
        ("h1", "4. Obligaciones para las herramientas de IA"),
        ("ul", [
            "Cada documento de la base documental del asistente lleva como metadatos: fecha de publicación, "
            "fecha de última revisión, estado y organismo emisor.",
            "El asistente debe indicar en su respuesta el estado del documento que cita.",
            "Los documentos en estado «Borrador» o «Retirada» no se cargan en la base documental.",
            "La base documental se revisa cada trimestre. Los documentos que cambian de estado se actualizan "
            "en un plazo máximo de 15 días.",
        ]),
        ("h1", "5. Responsables"),
        ("p", "El Comité de Guías (Dirección Médica, Farmacia, Calidad y un representante de cada servicio "
              "clínico) mantiene el registro de vigencia. Sistemas de Información aplica los cambios en la base "
              "documental del asistente."),
    ])


def doc_validacion():
    return ("NEXORA_Salud_Procedimiento_Validacion_Local_Modelos.pdf",
            "Procedimiento de validación local de modelos predictivos",
            "NEXORA Salud · Código PRC-IA-003 · Versión 1.0 · Aprobado por el Comité de IA el 3 de febrero de 2026",
            [
        ("h1", "1. Contexto"),
        ("p", "Un modelo que funciona bien en el hospital donde se desarrolló puede fallar en otro. Cambian los "
              "pacientes, la forma de registrar los datos y los circuitos asistenciales. La literatura recoge "
              "casos de modelos de alerta ampliamente implantados que, al validarse con pacientes de otro centro, "
              "detectaron muchos menos casos de los esperados y generaron una gran proporción de falsas alarmas. "
              "Este procedimiento existe para detectar esa situación antes de que afecte a los pacientes."),
        ("h1", "2. Fases"),
        ("tabla", ([
            ["Fase", "Qué se hace", "Duración orientativa"],
            ["1. Retrospectiva", "Se aplica el modelo a datos históricos de NEXORA Salud y se comparan sus predicciones con lo que ocurrió", "4-8 semanas"],
            ["2. Silenciosa", "El modelo funciona en tiempo real, pero sus alertas no se muestran a los profesionales", "3 meses"],
            ["3. Piloto supervisado", "Alertas visibles en una sola unidad, con revisión de cada alerta", "3 meses"],
            ["4. Despliegue", "Activación en el resto de unidades, con seguimiento trimestral", "Continuo"],
        ], [3.6 * cm, 9 * cm, 3.8 * cm])),
        ("h1", "3. Umbrales mínimos para pasar de fase"),
        ("p", "Para modelos de alerta clínica (por ejemplo, sepsis o deterioro):"),
        ("ul", [
            "<b>Sensibilidad</b> (casos reales que el modelo detecta): al menos el 70%.",
            "<b>Valor predictivo positivo</b> (alertas que resultan ser casos reales): al menos el 25%. Por debajo "
            "de ese valor, los profesionales tienden a ignorar las alertas.",
            "<b>Área bajo la curva ROC</b>: al menos 0,75 en la población propia.",
            "Resultados desglosados por <b>sexo, grupo de edad y centro</b>. Si algún grupo queda más de 10 "
            "puntos por debajo del global, el modelo no avanza de fase.",
        ]),
        ("h1", "4. Qué se exige al proveedor"),
        ("ul", [
            "Descripción de la población con la que se entrenó y validó el modelo.",
            "Validaciones externas publicadas o, en su defecto, acceso para realizar la fase 1.",
            "Compromiso de informar de cualquier cambio en el modelo con al menos 30 días de antelación.",
            "Marcado CE como producto sanitario cuando corresponda.",
        ]),
        ("h1", "5. Seguimiento"),
        ("p", "Tras el despliegue, el Comité de IA revisa cada trimestre la sensibilidad, el valor predictivo "
              "positivo y la proporción de alertas descartadas por los profesionales. Una caída de más de 10 puntos "
              "en cualquiera de ellos obliga a volver a la fase 2."),
    ])


def doc_diabetes():
    return ("NEXORA_Salud_Protocolo_Interno_Diabetes_2024.pdf",
            "Protocolo interno de control de la diabetes en consultas",
            "NEXORA Salud · Código PRT-END-014 · Versión 3.0 · Servicio de Endocrinología · Junio de 2024",
            [
        ("h1", "1. Objeto"),
        ("p", "Unificar los objetivos de control glucémico y los criterios de derivación en las consultas de "
              "atención primaria y endocrinología de NEXORA Salud. Este protocolo prevalece sobre las guías "
              "externas pendientes de actualización (ver POL-DOC-002)."),
        ("h1", "2. Objetivos de hemoglobina glicada (HbA1c) en adultos"),
        ("p", "Los objetivos se individualizan. Como referencia interna:"),
        ("tabla", ([
            ["Perfil del paciente", "Objetivo orientativo de HbA1c"],
            ["Adulto con diabetes tipo 2, sin complicaciones relevantes y bajo riesgo de hipoglucemia", "Menos del 7%"],
            ["Adulto con diabetes tipo 1", "Menos del 7%"],
            ["Mayor de 75 años, fragilidad o comorbilidad importante", "Entre el 7,5% y el 8%"],
            ["Esperanza de vida limitada", "Evitar síntomas; no se fija una cifra"],
        ], [10.4 * cm, 6 * cm])),
        ("p", "Si una herramienta de consulta devuelve una única cifra de HbA1c sin indicar el tipo de diabetes ni "
              "el perfil del paciente, la respuesta se considera <b>incompleta</b> y no debe aplicarse."),
        ("h1", "3. Criterios de derivación a endocrinología"),
        ("ul", [
            "Diabetes tipo 1 de nuevo diagnóstico.",
            "HbA1c por encima del objetivo individual durante más de 6 meses pese a ajustes de tratamiento.",
            "Hipoglucemias graves o repetidas.",
            "Embarazo o deseo gestacional en mujeres con diabetes.",
        ]),
        ("h1", "4. Revisión"),
        ("p", "Este protocolo se revisa cada dos años o cuando se publique una guía del SNS que afecte a su "
              "contenido. Próxima revisión prevista: junio de 2026 (<b>pendiente</b>)."),
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default="./nexora_salud_interno")
    args = ap.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for fn in (doc_protocolo_ia, doc_vigencia, doc_validacion, doc_diabetes):
        nombre, titulo, sub, bloques = fn()
        construir(out / nombre, titulo, sub, bloques)
        print("→", out / nombre)


if __name__ == "__main__":
    main()
