#!/usr/bin/env python3
"""
construir_inventario.py
=======================
Genera corpus_inventario.csv a partir de:
  · el catálogo público de GuíaSalud (https://portal.guiasalud.es/gpc/)
  · una lista fija de normativa y estrategia (UE, España, OMS, FDA, OCDE)
  · los documentos internos ficticios de NEXORA Salud

Capas:
  1 = Guías de práctica clínica del SNS (versión completa)
  2 = Material complementario de las guías (resúmenes, herramientas, material
      metodológico, revisiones, borradores de exposición pública, versiones en inglés)
  3 = Normativa, estrategia y orientaciones sobre IA y salud digital
  4 = Documentación interna de NEXORA Salud (ficticia, generada)

⚠️ Este script genera la BASE del inventario (capas 1-4, 122 documentos). La ampliación
(capa 3 extra y capa 5) la añade herramientas/ampliar_corpus.py. Si regeneras la base, se
pierde la ampliación: por eso el script se niega a sobrescribir un inventario más grande
salvo con --forzar.

Uso:
    python herramientas/construir_inventario.py            # descarga el catálogo
    python herramientas/construir_inventario.py --html gs.html
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: pip install requests")
    sys.exit(1)

CATALOGO = "https://portal.guiasalud.es/gpc/"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

# Guías que ya no están en el catálogo público pero sí en el corpus (se copian de disco)
GPC_LOCALES = [
    ("GPC_429_Diabetes_2_Osteba_compl.pdf", "web",
     "https://portal.guiasalud.es/wp-content/uploads/2018/12/GPC_429_Diabetes_2_Osteba_compl.pdf"),
    ("gpc_575_depresion_infancia_avaliat_compl_caduc.pdf", "local",
     "gpc_575_depresion_infancia_avaliat_compl_caduc.pdf"),
    ("gpc_584_merkel_compl.pdf", "local", "gpc_584_merkel_compl.pdf"),
    ("GPC_579_Guia_Adapta_Participacion_-Comunitaria.pdf", "local",
     "GPC_579_Guia_Adapta_Participacion_-Comunitaria.pdf"),
]

EURLEX = "https://eur-lex.europa.eu/legal-content/ES/TXT/PDF/?uri=CELEX:"
BOE = "https://www.boe.es/buscar/pdf/{a}/BOE-A-{a}-{n}-consolidado.pdf"
SNS_IA = "https://www.sanidad.gob.es/areas/saludDigital/estrategiaIASNS/doc/"
WHO = "https://iris.who.int/server/api/core/bitstreams/{}/content"

NORMATIVA = [
    # (fichero, título, categoría, fuente, url)
    ("AI_Act_Reglamento_UE_2024_1689.pdf", "AI Act — Reglamento Europeo de Inteligencia Artificial (UE 2024/1689)", "Regulacion_UE", "EUR-Lex", EURLEX + "32024R1689"),
    ("MDR_Reglamento_UE_2017_745_productos_sanitarios.pdf", "MDR — Reglamento de productos sanitarios (UE 2017/745)", "Regulacion_UE", "EUR-Lex", EURLEX + "32017R0745"),
    ("IVDR_Reglamento_UE_2017_746_diagnostico_in_vitro.pdf", "IVDR — Reglamento de productos sanitarios para diagnóstico in vitro (UE 2017/746)", "Regulacion_UE", "EUR-Lex", EURLEX + "32017R0746"),
    ("EHDS_Reglamento_UE_2025_327_espacio_datos_sanitarios.pdf", "EHDS — Espacio Europeo de Datos Sanitarios (Reglamento UE 2025/327)", "Regulacion_UE", "EUR-Lex", EURLEX + "32025R0327"),
    ("RGPD_Reglamento_UE_2016_679.pdf", "RGPD — Reglamento General de Protección de Datos (UE 2016/679)", "Regulacion_UE", "EUR-Lex", EURLEX + "32016R0679"),
    ("Ensayos_Clinicos_Reglamento_UE_536_2014.pdf", "Reglamento de ensayos clínicos con medicamentos de uso humano (UE 536/2014)", "Regulacion_UE", "EUR-Lex", EURLEX + "32014R0536"),
    ("HTA_Reglamento_UE_2021_2282_evaluacion_tecnologias.pdf", "Reglamento de evaluación de tecnologías sanitarias (UE 2021/2282)", "Regulacion_UE", "EUR-Lex", EURLEX + "32021R2282"),
    ("Directiva_UE_2011_24_asistencia_transfronteriza.pdf", "Directiva de derechos de los pacientes en la asistencia sanitaria transfronteriza (2011/24/UE)", "Regulacion_UE", "EUR-Lex", EURLEX + "32011L0024"),
    ("NIS2_Directiva_UE_2022_2555.pdf", "NIS2 — Directiva de ciberseguridad (UE 2022/2555), que incluye al sector sanitario", "Regulacion_UE", "EUR-Lex", EURLEX + "32022L2555"),
    ("Ley_41_2002_autonomia_paciente.pdf", "Ley 41/2002, básica reguladora de la autonomía del paciente y de la documentación clínica", "Regulacion_ES", "BOE", BOE.format(a=2002, n=22188)),
    ("Ley_14_1986_General_de_Sanidad.pdf", "Ley 14/1986, General de Sanidad", "Regulacion_ES", "BOE", BOE.format(a=1986, n=10499)),
    ("Ley_16_2003_cohesion_calidad_SNS.pdf", "Ley 16/2003, de cohesión y calidad del Sistema Nacional de Salud", "Regulacion_ES", "BOE", BOE.format(a=2003, n=10715)),
    ("Ley_44_2003_profesiones_sanitarias.pdf", "Ley 44/2003, de ordenación de las profesiones sanitarias", "Regulacion_ES", "BOE", BOE.format(a=2003, n=21340)),
    ("Ley_33_2011_salud_publica.pdf", "Ley 33/2011, General de Salud Pública", "Regulacion_ES", "BOE", BOE.format(a=2011, n=15623)),
    ("Ley_14_2007_investigacion_biomedica.pdf", "Ley 14/2007, de Investigación biomédica", "Regulacion_ES", "BOE", BOE.format(a=2007, n=12945)),
    ("RDL_1_2015_garantias_medicamentos.pdf", "Real Decreto Legislativo 1/2015, Ley de garantías y uso racional de los medicamentos", "Regulacion_ES", "BOE", BOE.format(a=2015, n=8343)),
    ("RD_192_2023_productos_sanitarios.pdf", "Real Decreto 192/2023, por el que se regulan los productos sanitarios", "Regulacion_ES", "BOE", BOE.format(a=2023, n=7416)),
    ("LOPDGDD_LO_3_2018.pdf", "LOPDGDD — Ley Orgánica 3/2018 de Protección de Datos Personales", "Regulacion_ES", "BOE", BOE.format(a=2018, n=16673)),
    ("Estrategia_IA_SNS_eIASNS_v13.pdf", "Estrategia de Inteligencia Artificial del Sistema Nacional de Salud (eIASNS)", "Estrategia_ES", "Ministerio de Sanidad", SNS_IA + "eIASNS_v13.pdf"),
    ("IASNS_Orientaciones_profesionales_uso_IA.pdf", "Orientaciones para profesionales sanitarios en el uso de la IA", "Estrategia_ES", "Ministerio de Sanidad", SNS_IA + "IASNS_Orientaciones_para_profesionales_sanitarios_en_el_uso_de_la_IA.pdf"),
    ("IASNS_Agente_transcripcion_funcionalidades.pdf", "Informe de funcionalidades del agente de transcripción clínica", "Estrategia_ES", "Ministerio de Sanidad", SNS_IA + "IASNS_Informe_de_funcionalidades_del_agente_de_transcripcion.pdf"),
    ("IASNS_Guia_proceso_marcado_CE.pdf", "Guía del proceso de marcado CE de productos sanitarios con IA en España", "Estrategia_ES", "Ministerio de Sanidad", SNS_IA + "IASNS_Guia_ProcesoMarcadoCE_Espana_PS.pdf"),
    ("IASNS_Omnibus_IA_simplificacion_MDR_IVDR.pdf", "Ómnibus de IA y simplificación de MDR/IVDR", "Estrategia_ES", "Ministerio de Sanidad", SNS_IA + "IASNS_OmnibusAI_SimplificacionMDR-IVDR.pdf"),
    ("OMS_Etica_gobernanza_IA_salud_2021.pdf", "OMS — Ethics and governance of artificial intelligence for health (2021)", "Orientaciones_OMS", "OMS", WHO.format("f780d926-4ae3-42ce-a6d6-e898a5562621")),
    ("OMS_Etica_IA_salud_modelos_multimodales_2024.pdf", "OMS — Guidance on large multi-modal models (2024)", "Orientaciones_OMS", "OMS", WHO.format("e9e62c65-6045-481e-bd04-20e206bc5039")),
    ("OMS_Consideraciones_regulatorias_IA_salud_2023.pdf", "OMS — Regulatory considerations on artificial intelligence for health (2023)", "Orientaciones_OMS", "OMS", WHO.format("ad62580f-540f-4e36-b957-e7f2946ae1fb")),
    ("OMS_Estrategia_global_salud_digital_2020_2025.pdf", "OMS — Global strategy on digital health 2020-2025", "Orientaciones_OMS", "OMS", WHO.format("1f4d4a08-b20d-4c36-9148-a59429ac3477")),
    ("FDA_Plan_accion_IA_ML_SaMD_2021.pdf", "FDA — AI/ML-Based Software as a Medical Device Action Plan (2021)", "Regulacion_EEUU", "FDA", "https://www.fda.gov/media/145022/download"),
    ("FDA_Buenas_practicas_ML_GMLP_2021.pdf", "FDA/Health Canada/MHRA — Good Machine Learning Practice guiding principles (2021)", "Regulacion_EEUU", "FDA", "https://www.fda.gov/media/153486/download"),
    ("FDA_Guia_PCCP_dispositivos_IA.pdf", "FDA — Predetermined Change Control Plans for AI-enabled device software functions", "Regulacion_EEUU", "FDA", "https://www.fda.gov/media/166704/download"),
    ("OCDE_Accion_colectiva_IA_responsable_salud_2024.pdf", "OCDE — Collective action for responsible AI in health (2024)", "Orientaciones_OCDE", "OCDE", "https://www.oecd.org/content/dam/oecd/en/publications/reports/2024/01/collective-action-for-responsible-ai-in-health_9a65136f/f2050177-en.pdf"),
]

INTERNOS = [
    ("NEXORA_Salud_Protocolo_Uso_IA_Clinica_v2.1.pdf", "NEXORA Salud — Protocolo de uso de IA en la práctica clínica (v2.1) [FICTICIO]"),
    ("NEXORA_Salud_Politica_Vigencia_Guias_Clinicas.pdf", "NEXORA Salud — Política de vigencia de guías y protocolos clínicos [FICTICIO]"),
    ("NEXORA_Salud_Procedimiento_Validacion_Local_Modelos.pdf", "NEXORA Salud — Procedimiento de validación local de modelos predictivos [FICTICIO]"),
    ("NEXORA_Salud_Protocolo_Interno_Diabetes_2024.pdf", "NEXORA Salud — Protocolo interno de control de la diabetes en consultas (2024) [FICTICIO]"),
]

COMPLEMENTOS = [
    ("resum_ingles", "resumen en inglés"), ("_ingles", "versión en inglés"), ("_en.pdf", "versión en inglés"),
    ("resum", "resumen"), ("rapid", "guía rápida"), ("herram", "herramientas"),
    ("adenda", "adenda"), ("revision", "revisión de vigencia"), ("mat_met", "material metodológico"),
    ("exp_pub", "borrador de exposición pública"), ("exposicion_publica", "borrador de exposición pública"),
    ("infografia", "infografía"),
]

ESPECIALIDAD = [
    ("diabetes", "Endocrinologia"), ("obesidad", "Endocrinologia"), ("osteoporosis", "Reumatologia"),
    ("artritis", "Reumatologia"), ("espoguia", "Reumatologia"), ("depresion", "Salud_mental"),
    ("ansiedad", "Salud_mental"), ("suicida", "Salud_mental"), ("tmg", "Salud_mental"),
    ("toc", "Salud_mental"), ("autista", "Salud_mental"), ("ictus", "Neurologia"),
    ("parkinson", "Neurologia"), ("neurorehabilitacion", "Neurologia"), ("periodont", "Odontologia"),
    ("bucal", "Odontologia"), ("molares", "Odontologia"), ("implant", "Odontologia"),
    ("boca_seca", "Odontologia"), ("cancer_oral", "Odontologia"), ("paliativ", "Cuidados_paliativos"), ("palitativ", "Cuidados_paliativos"),
    ("covid", "Pediatria"), ("respiratorio", "Pediatria"), ("canguro", "Pediatria"),
    ("gesepoc", "Neumologia"), ("tabaquismo", "Neumologia"), ("toracico", "Urgencias"),
    ("hemocultivos", "Microbiologia"), ("subcutanea", "Enfermeria"), ("anticoncepcion", "Ginecologia"),
    ("embarazo", "Ginecologia"), ("mama", "Oncologia"), ("merkel", "Oncologia"),
    ("catarata", "Oftalmologia"), ("participacion", "Salud_publica"),
]


TITULOS = {
    "429": "Diabetes mellitus tipo 2 (2008)",
    "453": "Trastorno mental grave",
    "481": "Prevención y tratamiento de la conducta suicida",
    "534": "Manejo de la depresión en el adulto",
    "575": "Depresión mayor en la infancia y la adolescencia",
    "579": "Participación comunitaria en salud",
    "584": "Carcinoma de células de Merkel",
    "585": "Anticoncepción",
    "604": "Traumatismo torácico",
    "608": "Periodontitis",
    "612": "Atención paliativa al adulto",
    "613": "Antibióticos en implantología oral",
    "614": "COVID-19 en pediatría",
    "618": "Cuidados paliativos pediátricos",
    "619": "Enfermedad de Parkinson",
    "620": "Atención odontológica en el paciente con cáncer oral",
    "621": "Tratamiento de la periodontitis",
    "622": "Cirugía bucal en pacientes con trastornos de la coagulación",
    "623": "Actividad física durante el embarazo",
    "624": "Osteoporosis",
    "625": "Prevención secundaria del ictus",
    "626": "Terceros molares",
    "630": "Tratamiento del tabaquismo",
    "631": "Abordaje de procesos bucales",
    "633": "Método madre canguro",
    "634": "Trastorno obsesivo-compulsivo en la infancia y la adolescencia",
    "635": "Manejo del ictus en atención primaria",
    "636": "Espondiloartritis (ESPOGUIA)",
    "641": "Trastornos de ansiedad",
    "644": "Neurorrehabilitación",
    "645": "Enfermedades periimplantarias",
    "649": "Boca seca",
    "650": "Obesidad",
    "651": "Hemocultivos",
    "652": "Trastorno del espectro autista en atención primaria",
    "653": "Artritis reumatoide",
    "657": "Infecciones del tracto respiratorio superior en pediatría",
    "658": "Uso de la vía subcutánea en el hospital",
    "659": "Diabetes mellitus tipo 1 (2026)",
    "662": "Catarata en el paciente adulto",
    "664": "Cáncer de mama metastásico",
}


def especialidad(nombre: str) -> str:
    n = nombre.lower()
    for clave, esp in ESPECIALIDAD:
        if clave in n:
            return esp
    return "Otras"


def titulo_gpc(nombre: str, extra: str = "") -> str:
    if nombre.lower().startswith("gesepoc"):
        t = "Guía española de la EPOC (GesEPOC 2021)"
    else:
        m = re.match(r"(?i)gpc_(\d+)_", nombre)
        num = m.group(1) if m else ""
        t = f"GPC {num} del SNS — {TITULOS.get(num, nombre)}"
        if "adapta" in nombre.lower():
            t += " (Guía Adapta)"
        if "_en.pdf" in nombre.lower() or "ingles" in nombre.lower():
            extra = extra or "versión en inglés"
        if "gall" in nombre.lower():
            extra = (extra + ", en gallego").strip(", ")
    return t + (f" · {extra}" if extra else "")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", help="HTML del catálogo ya descargado (opcional)")
    ap.add_argument("--salida", default="corpus_inventario.csv")
    ap.add_argument("--forzar", action="store_true",
                    help="sobrescribir aunque el inventario actual tenga más documentos")
    args = ap.parse_args()
    destino = Path(args.salida)
    if destino.exists() and not args.forzar:
        with open(destino, encoding="utf-8") as f:
            existentes = sum(1 for _ in f) - 1
        if existentes > 130:
            sys.exit(f"El inventario actual tiene {existentes} documentos (ampliado). "
                     "Usa --salida otro.csv, o --forzar si de verdad quieres regenerarlo.")

    html = Path(args.html).read_text(encoding="utf-8", errors="ignore") if args.html \
        else requests.get(CATALOGO, headers=UA, timeout=60).text
    urls = sorted(set(re.findall(r"https://portal\.guiasalud\.es/wp-content/uploads/[^\"']+?\.pdf", html)))

    filas = []
    completas, complementos = [], []
    for u in urls:
        nombre = u.rsplit("/", 1)[1]
        tipo = next((etq for clave, etq in COMPLEMENTOS if clave in nombre.lower()), None)
        (complementos if tipo else completas).append((nombre, u, tipo))

    nid = 0
    def add(capa, fichero, titulo, categoria, fuente, tipo, url):
        nonlocal nid
        nid += 1
        filas.append([f"{nid:03d}", f"{nid:03d}_{fichero}", titulo, capa, categoria, fuente, tipo, url])

    for nombre, u, _ in completas:
        add(1, nombre, titulo_gpc(nombre), especialidad(nombre), "GuiaSalud", "web", u)
    for nombre, tipo, u in GPC_LOCALES:
        extra = "caducada" if "caduc" in nombre else ""
        add(1, nombre, titulo_gpc(nombre, extra), especialidad(nombre), "GuiaSalud", tipo, u)
    for nombre, u, tipo in complementos:
        add(2, nombre, titulo_gpc(nombre, tipo), especialidad(nombre), "GuiaSalud", "web", u)
    for fichero, titulo, cat, fuente, u in NORMATIVA:
        add(3, fichero, titulo, cat, fuente, "web", u)
    for fichero, titulo in INTERNOS:
        add(4, fichero, titulo, "Interno_NEXORA", "NEXORA Salud", "local", fichero)

    with open(args.salida, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["id", "filename", "titulo", "capa", "categoria", "fuente", "tipo_descarga", "urls"])
        w.writerows(filas)
    por_capa = {}
    for r in filas:
        por_capa[r[3]] = por_capa.get(r[3], 0) + 1
    print(f"→ {args.salida}: {len(filas)} documentos · por capa: {por_capa}")


if __name__ == "__main__":
    main()
