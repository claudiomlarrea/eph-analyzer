#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Anexo III GEMEPH desarrollado para evaluación de Consejo Superior."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

TEMPLATE = Path("/Users/claudiolarrea/Downloads/3 Anexo III. Presentación de informes finales (1).docx")
OUT = Path("/Users/claudiolarrea/Library/CloudStorage/OneDrive-Personal/11 Investigacion/2026/GEMEPH")
RES = OUT / "02_Resultados_empiricos"


def set_run_font(run, size=11, bold=False, italic=False):
    run.bold = bold
    run.italic = italic
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn("w:ascii"), "Times New Roman")
    rFonts.set(qn("w:hAnsi"), "Times New Roman")


def main() -> None:
    js = json.loads((RES / "GEMEPH_resumen_3escenarios_2022_2024_T4_tic_20260821.json").read_text())
    xlsx = RES / "GEMEPH_resultados_3escenarios_2022_2024_T4_tic_20260821.xlsx"
    cat = pd.read_excel(xlsx, sheet_name="catalogo_31_aglomerados")
    aglo = cat[cat["tipo"] == "aglomerado"].copy()
    top_exc = aglo.nlargest(5, "idx_exclusion_digital")
    low_exc = aglo.nsmallest(3, "idx_exclusion_digital")
    top_vuln = aglo.nlargest(3, "vulnerabilidad_social")
    b = js["baseline_kpis"]
    levers = js["levers_oficiales"]
    esc = {e["id"]: e for e in js["escenarios"]}
    vuln_txt = ", ".join(
        f"{r.territorio_nombre} ({r.vulnerabilidad_social:.4f})" for r in top_vuln.itertuples()
    )

    shutil.copy2(TEMPLATE, "/tmp/Anexo_III_GEMEPH_CS.docx")
    doc = Document("/tmp/Anexo_III_GEMEPH_CS.docx")
    body = doc.element.body
    for child in list(body):
        if not child.tag.endswith("sectPr"):
            body.remove(child)

    def add_p(
        text="",
        *,
        bold=False,
        italic=False,
        size=11,
        space_after=8,
        space_before=0,
        align="left",
        first_indent=False,
        hanging=False,
    ):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.space_after = Pt(space_after)
        pf.space_before = Pt(space_before)
        pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        if align == "center":
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif align == "justify":
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if first_indent:
            pf.first_line_indent = Cm(1.25)
        if hanging:
            pf.left_indent = Cm(1.27)
            pf.first_line_indent = Cm(-1.27)
        if text:
            run = p.add_run(text)
            set_run_font(run, size=size, bold=bold, italic=italic)
        return p

    def add_h(text, level=1):
        size = {1: 14, 2: 12}.get(level, 11)
        return add_p(text, bold=True, size=size, space_before=14, space_after=8)

    def add_lv(label, value):
        p = add_p(align="justify", space_after=6)
        r1 = p.add_run(label)
        set_run_font(r1, bold=True)
        r2 = p.add_run(value)
        set_run_font(r2, bold=False)
        return p

    add_p("UNIVERSIDAD CATÓLICA DE CUYO", bold=True, size=14, align="center", space_after=2)
    add_p(
        "Secretaría de Investigación y Vinculación Tecnológica",
        bold=True,
        size=12,
        align="center",
        space_after=16,
    )
    add_p(
        "INFORME FINAL DEL PROYECTO DE INVESTIGACIÓN",
        bold=True,
        size=16,
        align="center",
        space_after=18,
    )

    add_lv(
        "Título del Proyecto: ",
        "GEMEPH — Gemelo digital sociodemográfico de la EPH-INDEC: exclusión digital, vulnerabilidad y brechas territoriales en Argentina",
    )
    add_lv("Director/a: ", "Claudio Marcelo Larrea Arnau")
    add_lv("Co-director/a: ", "José La Malfa")
    add_lv(
        "Unidad Académica: ",
        "Observatorio de Inteligencia Artificial — Universidad Católica de Cuyo",
    )
    add_lv("Resolución de Aprobación Nº: ", "(a completar por la Secretaría de Investigación)")
    add_lv(
        "Período Informado: ",
        "Enero 2025 – Diciembre 2025 (ejecución); evidencia empírica EPH-INDEC 2022–2024 (4.º trimestre, módulo TIC)",
    )
    add_lv("Fecha de Presentación: ", "21 de agosto de 2026")
    doc.add_page_break()

    add_h("Sección 1. Identificación y estado general")
    add_lv(
        "Denominación del Proyecto: ",
        "GEMEPH: Desarrollo y validación de un Gemelo Digital Sociodemográfico Territorial basado en la Encuesta Permanente de Hogares (EPH-INDEC) para el análisis, simulación y apoyo a la toma de decisiones mediante Inteligencia Artificial.",
    )
    add_lv(
        "Director/a: ",
        "Claudio Marcelo Larrea Arnau (Doctor en Ciencias Sociales; Doctor en Educación; Magíster en Educación; Categoría I Superior).",
    )
    add_lv(
        "Equipo de trabajo: ",
        "José La Malfa (Co-director; desarrollo tecnológico e integración de datos); Javier Coria (modelado de IA/ML y escenarios); Stefania Young (documentación, calidad de datos y visualización); Laura Pizarro (apoyo académico-institucional). Filiación: Observatorio de Inteligencia Artificial, UCCuyo.",
    )
    add_lv(
        "Unidad Académica: ",
        "Observatorio de Inteligencia Artificial — Universidad Católica de Cuyo.",
    )
    add_lv(
        "Fuente de financiamiento: ",
        "Interna (adscripción institucional, infraestructura UCCuyo y software de código abierto).",
    )
    add_lv("Duración del Proyecto: ", "12 meses.")
    add_lv(
        "Período informado: ",
        "Ciclo de ejecución 2025; resultados empíricos sobre panel EPH 2022–2024 (T4, TIC).",
    )

    add_h("Ejecución presupuestaria", 2)
    add_lv("Presupuesto total asignado: ", "$0 (cero pesos).")
    add_lv("Presupuesto ejecutado: ", "$0 (cero pesos).")
    add_lv(
        "Porcentaje de ejecución: ",
        "100% respecto del presupuesto asignado ($0). Todas las actividades se ejecutaron con recursos institucionales (tiempo docente-investigador, equipamiento existente y herramientas open source).",
    )
    add_lv(
        "Fuente de financiamiento: ",
        "Interna — Observatorio de Inteligencia Artificial / Secretaría de Investigación y Vinculación Tecnológica.",
    )
    add_lv(
        "Observaciones o rendición externa: ",
        "No aplica. No se recibieron ni ejecutaron fondos dinerarios externos. No existen observaciones de auditoría externa vinculadas a este proyecto.",
    )
    add_p(
        "Estado general del proyecto: se considera cumplido en sus seis objetivos específicos. "
        "Existe infraestructura tecnológica operativa (GEMEPH), evidencia empírica reproducible sobre microdatos oficiales "
        "y productos de transferencia (plataforma pública, Excel, informes Word y el presente Anexo III).",
        align="justify",
        first_indent=True,
    )

    add_h("Sección 2. Resumen ejecutivo")
    add_h("Síntesis de los resultados más significativos", 2)
    add_p(
        "GEMEPH construyó y validó un gemelo digital sociodemográfico territorial que toma como baseline los microdatos oficiales "
        "de la Encuesta Permanente de Hogares (INDEC) y los expone a escenarios ficticios (what-if) para anticipar magnitudes de cambio "
        "en exclusión digital, vulnerabilidad social, movilidad social proxy, educación y empleo. La corrida de referencia integra "
        f"{b['n_individuos']:,} registros individuales del período 2022–2024 (4.º trimestre, módulo TIC), con expansión poblacional "
        f"aproximada de {b['peso_expansion']:,.0f} personas, y un catálogo comparable de Argentina más 31 aglomerados urbanos "
        f"({int(cat.shape[0])} unidades territoriales en el archivo de resultados).",
        align="justify",
        first_indent=True,
    )
    add_p(
        f"En el baseline oficial nacional, el índice de exclusión digital es {b['idx_exclusion_digital']:.4f}; "
        f"el porcentaje de exclusión digital alta, {b['pct_exclusion_digital_alta']:.2f}%; "
        f"la vulnerabilidad social, {b['vulnerabilidad_social']:.4f}; "
        f"la movilidad social proxy, {b['score_movilidad_proxy']:.4f}; "
        f"la ocupación, {b['pct_ocupado']:.2f}%; la educación superior completa, {b['pct_superior']:.2f}%; "
        f"y la informalidad entre ocupados, {b['pct_informal_ocupados']:.2f}%. "
        f"La brecha de ocupación mujer–hombre es de {b['brechas']['ocupacion_mujer_menos_hombre_pp']:.2f} puntos porcentuales. "
        f"Entre aglomerados, la mayor exclusión digital aparece en {top_exc.iloc[0]['territorio_nombre']} "
        f"({top_exc.iloc[0]['idx_exclusion_digital']:.4f}), {top_exc.iloc[1]['territorio_nombre']} "
        f"({top_exc.iloc[1]['idx_exclusion_digital']:.4f}) y {top_exc.iloc[2]['territorio_nombre']} "
        f"({top_exc.iloc[2]['idx_exclusion_digital']:.4f}); la menor, en {low_exc.iloc[0]['territorio_nombre']} "
        f"({low_exc.iloc[0]['idx_exclusion_digital']:.4f}).",
        align="justify",
        first_indent=True,
    )
    add_p(
        "El aporte distintivo del gemelo no es sustituir al dato oficial, sino simular. Sobre el mismo baseline se ejecutaron tres escenarios ficticios: "
        "E1 (conectividad inclusiva en el quintil de menores ingresos), E2 (expansión de educación superior al 40%) y E3 (paquete integrado de "
        "formalización laboral al 90% y educación superior al 30%). E1 produce un ajuste marginal de la exclusión (la conectividad oficial del "
        f"quintil bajo ya es elevada: {levers['internet_quintil_i']}%), mientras que E2 eleva la movilidad proxy en "
        f"{esc['E2']['deltas']['score_movilidad_proxy']:+.4f} y la educación superior en {esc['E2']['deltas']['pct_superior']:+.2f} pp, "
        f"y E3 combina mejoras educativas ({esc['E3']['deltas']['pct_superior']:+.2f} pp) con formalización y un leve descenso de exclusión predicha "
        f"({esc['E3']['modelo']['pct_exclusion_predicho_base']}% → {esc['E3']['modelo']['pct_exclusion_predicho_escenario']}%). "
        "La plataforma pública https://eph-analyzer.streamlit.app/GEMEPH habilita consulta, comparación territorial y nueva simulación.",
        align="justify",
        first_indent=True,
    )

    add_h("Metodología")
    add_lv(
        "Diseño del estudio: ",
        "Investigación aplicada tecnológica con enfoque cuantitativo, descriptivo-analítico y longitudinal, enmarcada en Design Science Research (DSR). "
        "El artefacto es GEMEPH: gemelo digital que representa el estado sociodemográfico con microdatos EPH, construye baselines territoriales "
        "y ejecuta escenarios contrafactuales. No busca inferencia causal experimental, sino reproducibilidad, trazabilidad y utilidad para investigación y decisión.",
    )
    add_lv(
        "Bases de datos y fuentes utilizadas: ",
        "Microdatos públicos y anonimizados de la EPH (INDEC), bases de hogar e individuo con módulo TIC. Período empírico: 2022, 2023 y 2024, 4.º trimestre. "
        "Integración automatizada con eph-analyzer / GEMEPH. No se usaron datos personales identificables ni fuentes privadas de pago.",
    )
    add_lv(
        "Variables analizadas: ",
        "Indicadores ponderados (PONDERA): exclusión digital; % exclusión alta; vulnerabilidad social; movilidad social proxy; ocupación; "
        "educación secundaria y superior; informalidad; brechas de género; brechas de internet por quintiles; perfiles por k-means. "
        "Palancas de simulación: internet en quintil I, educación universitaria completa y empleo formal.",
    )
    add_lv(
        "Herramientas de análisis (software / IA / estadística): ",
        "Python; pandas; NumPy; scikit-learn (k-means y regresión logística); estadística ponderada; Streamlit; Plotly; openpyxl; python-docx; Parquet. "
        "Despliegue en Streamlit Cloud. Repositorio eph-analyzer.",
    )
    add_lv(
        "Procedimientos de validación de resultados: ",
        f"(1) Control de calidad de microdatos (n={b['n_individuos']:,}). (2) KPIs ponderados. (3) Catálogo de 31 aglomerados + nacional. "
        "(4) Exportación Excel/Word/JSON. (5) Contraste baseline vs. E1–E3 con deltas y predicción de exclusión alta. (6) Coherencia con OE1–OE6 del Anexo I.",
    )
    add_lv(
        "Limitaciones del estudio: ",
        "EPH urbana; TIC concentrada en trimestres específicos; escenarios contrafactuales (no son proyección oficial ni causalidad); "
        "dependencia de la actualización de bases INDEC.",
    )

    add_h("Resultados y discusión")
    add_h("2.1. Baseline oficial: el dato real que el gemelo representa", 2)
    add_p(
        "El punto de partida de GEMEPH es siempre el dato oficial. En la corrida 2022–2024 (T4, TIC), el panel nacional "
        f"reúne {b['n_individuos']:,} personas de la muestra EPH. Los indicadores ponderados describen un país urbano con "
        f"ocupación cercana a {b['pct_ocupado']:.1f}%, educación superior completa en torno a {b['pct_superior']:.1f}% "
        f"y un índice de exclusión digital de {b['idx_exclusion_digital']:.4f}, con {b['pct_exclusion_digital_alta']:.2f}% "
        "en exclusión digital alta. La vulnerabilidad social "
        f"({b['vulnerabilidad_social']:.4f}) y la movilidad proxy ({b['score_movilidad_proxy']:.4f}) completan la lectura estructural.",
        align="justify",
        first_indent=True,
    )
    add_p(
        f"Las palancas oficiales —internet en quintil bajo {levers['internet_quintil_i']}%, "
        f"educación superior {levers['pct_superior']}% y empleo formal {levers['pct_empleo_formal']}%— anclan toda simulación. "
        "GEMEPH no inventa la realidad social: la representa con fuentes públicas y luego pregunta qué ocurriría si esas palancas cambiaran.",
        align="justify",
        first_indent=True,
    )

    add_h("2.2. Brechas territoriales entre los 31 aglomerados", 2)
    add_p(
        "El catálogo territorial compara aglomerados con la misma metodología. Los cinco con mayor exclusión digital son:",
        align="justify",
        first_indent=True,
    )
    for _, r in top_exc.iterrows():
        add_p(
            f"• {r['territorio_nombre']}: exclusión {r['idx_exclusion_digital']:.4f}; "
            f"vulnerabilidad {r['vulnerabilidad_social']:.4f}; movilidad proxy {r['score_movilidad_proxy']:.4f}; "
            f"ocupación {r['pct_ocupado']:.2f}%; superior {r['pct_superior']:.2f}%.",
            space_after=4,
        )
    add_p(
        f"En el extremo opuesto, {low_exc.iloc[0]['territorio_nombre']} presenta la exclusión más baja "
        f"({low_exc.iloc[0]['idx_exclusion_digital']:.4f}). En vulnerabilidad social destacan {vuln_txt}. "
        "Estas diferencias confirman que existen brechas territoriales medibles y actualizables con cada publicación de microdatos.",
        align="justify",
        first_indent=True,
    )

    add_h("2.3. Función del gemelo: de lo oficial a lo contrafactual", 2)
    add_p(
        "La utilidad de GEMEPH reside en exponer el baseline oficial a escenarios ficticios controlados. Un escenario no es un pronóstico: "
        "es un experimento computacional que modifica palancas (conectividad, educación, formalidad) y recalcula indicadores y, "
        "cuando corresponde, la probabilidad predicha de exclusión digital alta. Así se obtienen deltas para política, docencia e investigación, "
        "sin confundir simulación con estadística oficial.",
        align="justify",
        first_indent=True,
    )

    e = esc["E1"]
    add_h("2.4. Escenario ficticio E1 — Conectividad inclusiva (quintil de menores ingresos)", 2)
    add_p(e["narrativa"], align="justify", first_indent=True)
    add_p(
        f"Metas: internet en quintil I = {e['targets']['internet_quintil_i']}% (oficial {levers['internet_quintil_i']}%); "
        f"educación superior y empleo formal en valores oficiales ({e['targets']['pct_superior']}% y {e['targets']['pct_empleo_formal']}%).",
        align="justify",
        first_indent=True,
    )
    add_p(
        f"Resultados: exclusión digital de {b['idx_exclusion_digital']:.4f} a {e['scenario_kpis']['idx_exclusion_digital']:.4f} "
        f"(Δ {e['deltas']['idx_exclusion_digital']:+.4f}); % exclusión alta de {b['pct_exclusion_digital_alta']:.2f}% a "
        f"{e['scenario_kpis']['pct_exclusion_digital_alta']:.2f}% (Δ {e['deltas']['pct_exclusion_digital_alta']:+.2f} pp); "
        f"vulnerabilidad de {b['vulnerabilidad_social']:.4f} a {e['scenario_kpis']['vulnerabilidad_social']:.4f}. "
        f"Predicción de exclusión alta: {e['modelo']['pct_exclusion_predicho_base']}% → {e['modelo']['pct_exclusion_predicho_escenario']}%. "
        f"Brecha internet Q1–Q5: {b['brechas']['internet_q1_menos_q5_pp']:+.2f} pp → "
        f"{e['scenario_kpis']['brechas']['internet_q1_menos_q5_pp']:+.2f} pp.",
        align="justify",
        first_indent=True,
    )
    add_p(
        "Discusión crítica: el impacto es pequeño porque la cobertura oficial de internet en el quintil bajo ya es muy alta "
        f"({levers['internet_quintil_i']}%). Cuando la conectividad está cerca de la saturación, políticas solo digitales aportan "
        "ganancias marginales sobre indicadores agregados. El gemelo evita sobreprometer efectos de acceso puro.",
        align="justify",
        first_indent=True,
    )

    e = esc["E2"]
    add_h("2.5. Escenario ficticio E2 — Expansión educativa superior", 2)
    add_p(e["narrativa"], align="justify", first_indent=True)
    add_p(
        f"Metas: educación superior = {e['targets']['pct_superior']}% (oficial {levers['pct_superior']}%); "
        "internet quintil I y empleo formal fijos en niveles oficiales.",
        align="justify",
        first_indent=True,
    )
    add_p(
        f"Resultados: educación superior {e['scenario_kpis']['pct_superior']:.2f}% (Δ {e['deltas']['pct_superior']:+.2f} pp); "
        f"movilidad proxy de {b['score_movilidad_proxy']:.4f} a {e['scenario_kpis']['score_movilidad_proxy']:.4f} "
        f"(Δ {e['deltas']['score_movilidad_proxy']:+.4f}). La exclusión digital agregada permanece en "
        f"{e['scenario_kpis']['idx_exclusion_digital']:.4f} (Δ {e['deltas']['idx_exclusion_digital']:+.4f}); "
        f"predicción de exclusión alta: {e['modelo']['pct_exclusion_predicho_escenario']}%.",
        align="justify",
        first_indent=True,
    )
    add_p(
        "Discusión crítica: E2 muestra que el canal educativo es especialmente sensible para la movilidad proxy. "
        "Un salto contrafactual al 40% de educación superior no borra automáticamente la exclusión digital agregada, "
        "pero desplaza con claridad el indicador de oportunidades relativas. GEMEPH discrimina canales de impacto.",
        align="justify",
        first_indent=True,
    )

    e = esc["E3"]
    add_h("2.6. Escenario ficticio E3 — Formalización laboral + educación (paquete integrado)", 2)
    add_p(e["narrativa"], align="justify", first_indent=True)
    add_p(
        f"Metas: empleo formal = {e['targets']['pct_empleo_formal']}% (oficial {levers['pct_empleo_formal']}%); "
        f"educación superior = {e['targets']['pct_superior']}%; internet quintil I = {e['targets']['internet_quintil_i']}%.",
        align="justify",
        first_indent=True,
    )
    add_p(
        f"Resultados: educación superior {e['scenario_kpis']['pct_superior']:.2f}% (Δ {e['deltas']['pct_superior']:+.2f} pp); "
        f"movilidad proxy {e['scenario_kpis']['score_movilidad_proxy']:.4f} (Δ {e['deltas']['score_movilidad_proxy']:+.4f}); "
        f"exclusión digital {e['scenario_kpis']['idx_exclusion_digital']:.4f} (Δ {e['deltas']['idx_exclusion_digital']:+.4f}); "
        f"% exclusión alta {e['scenario_kpis']['pct_exclusion_digital_alta']:.2f}% "
        f"(Δ {e['deltas']['pct_exclusion_digital_alta']:+.2f} pp); "
        f"predicción {e['modelo']['pct_exclusion_predicho_base']}% → {e['modelo']['pct_exclusion_predicho_escenario']}%.",
        align="justify",
        first_indent=True,
    )
    add_p(
        "Discusión crítica: E3 representa un paquete más realista (educación + formalización + mejora parcial de conectividad). "
        "El gemelo registra mejoras en movilidad proxy y un descenso leve de exclusión predicha, sin exagerar efectos agregados. "
        "Sirve para evaluar combinaciones de medidas antes de formular intervenciones, siempre como simulación.",
        align="justify",
        first_indent=True,
    )

    add_h("2.7. Lectura integrada y vinculación con el marco del proyecto", 2)
    add_p(
        "Comparando E1, E2 y E3 sobre el mismo baseline: (a) la conectividad adicional en hogares ya conectados aporta retornos decrecientes; "
        "(b) la expansión educativa mueve con fuerza la movilidad proxy; (c) los paquetes integrados producen cambios más equilibrados. "
        "El valor del artefacto está en la representación dinámica y en la exploración de escenarios, no en reemplazar estadísticas oficiales. "
        "Con ello se cumplen empíricamente OE3 (modelado), OE4 (plataforma) y OE5 (validación) del Anexo I.",
        align="justify",
        first_indent=True,
    )

    add_h("Sección 3.1. Cronograma y objetivos")
    add_p(
        "La ejecución se organizó en seis etapas alineadas a los objetivos específicos. El porcentaje de avance refleja el cierre del período informado.",
        align="justify",
        first_indent=True,
    )

    table = doc.add_table(rows=7, cols=6)
    headers = [
        "Objetivo específico",
        "Actividades planificadas",
        "Actividades ejecutadas",
        "% avance",
        "Evidencias / entregables",
        "Comentarios / desvíos",
    ]
    rows = [
        [
            "OE1. Arquitectura conceptual, metodológica y tecnológica",
            "Definir componentes, datos y actualización",
            "Arquitectura implementada: panel, catálogo, baselines y motor de escenarios",
            "100%",
            "módulo gemeph/; https://eph-analyzer.streamlit.app/GEMEPH",
            "Sin desvíos",
        ],
        [
            "OE2. Integrar y normalizar microdatos EPH-INDEC",
            "ETL, validación y base multi-año",
            f"Panel 2022–2024 T4 TIC validado (n={b['n_individuos']:,})",
            "100%",
            "Parquet/panel; catalogo_31_aglomerados",
            "Actualizable con nuevas bases",
        ],
        [
            "OE3. Modelos IA/ML y simulación",
            "Clustering, predicción y what-if",
            "Clústeres + logística + escenarios E1–E3",
            "100%",
            "Excel 3escenarios (detalle_E1/E2/E3)",
            "Contrafactuales (no oficiales)",
        ],
        [
            "OE4. Plataforma interactiva",
            "Visualización, consulta y simulación",
            "Plataforma publicada y operativa",
            "100%",
            "https://eph-analyzer.streamlit.app/GEMEPH",
            "Sin desvíos",
        ],
        [
            "OE5. Validación técnico-científica",
            "Calidad, predictividad y utilidad",
            "KPIs nacionales, ranking 31 aglomerados y deltas E1–E3",
            "100%",
            "comparacion_baseline_vs_3E",
            "Limitaciones EPH urbana explicitadas",
        ],
        [
            "OE6. Documentación y transferencia",
            "Informes y productos tecnológicos",
            "Excel, Word, Anexo III e infraestructura Observatorio IA",
            "100%",
            "Carpeta GEMEPH/; Anexo_III_Informe_Final_GEMEPH.docx",
            "Artículo en preparación",
        ],
    ]
    for j, h in enumerate(headers):
        table.rows[0].cells[j].text = h
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            table.rows[i].cells[j].text = val

    add_p("")
    add_p(
        "Justificación de desvíos: no hay desvíos sustanciales. La producción de artículos indexados permanece en curso (OE6), "
        "sin afectar el cumplimiento tecnológico ni la evidencia empírica del informe final.",
        align="justify",
        first_indent=True,
    )

    add_h("Sección 3.2. Producción y transferencia")
    add_lv(
        "Artículos publicados: ",
        "En preparación. Se proyecta al menos un artículo sobre arquitectura GEMEPH, baseline EPH 2022–2024 y escenarios E1–E3, "
        "orientado a ciencias sociales computacionales / ciencia de datos aplicadas.",
    )
    add_lv(
        "Ponencias y congresos: ",
        "Previstas en Jornadas de Investigación UCCuyo y eventos de IA aplicada y analítica de políticas públicas. "
        "Los tableros GEMEPH son material demostrable.",
    )
    add_lv(
        "Productos tecnológicos (aplicaciones, tableros, informes): ",
        "(1) Plataforma https://eph-analyzer.streamlit.app/GEMEPH; "
        "(2) Excel territorial y de 3 escenarios; "
        "(3) Informes Word; "
        "(4) Pipelines reproducibles (gemeph/ e indec_auto/); "
        "(5) Persistencia de paneles/baselines para actualización periódica.",
    )
    add_lv(
        "Formación de recursos humanos (tesis, becarios, estudiantes): ",
        "José La Malfa, Javier Coria, Stefania Young y Laura Pizarro participaron en datos, modelado, documentación y apoyo institucional. "
        "GEMEPH queda como laboratorio digital para trabajos finales, tesis y semilleros del Observatorio de IA.",
    )
    add_lv(
        "Actividades de divulgación: ",
        "Tablero abierto; informes técnicos para la Secretaría de Investigación; insumos para organismos interesados en exclusión digital, "
        "vulnerabilidad y brechas territoriales; comunicación institucional del Observatorio.",
    )

    add_h("Conclusiones y proyecciones")
    add_lv(
        "Principales conclusiones: ",
        "1) Se consolidó GEMEPH como gemelo digital sociodemográfico operativo sobre EPH-INDEC. "
        f"2) Baseline oficial 2022–2024 (T4): exclusión {b['idx_exclusion_digital']:.4f}, "
        f"vulnerabilidad {b['vulnerabilidad_social']:.4f}, movilidad proxy {b['score_movilidad_proxy']:.4f}, "
        "con heterogeneidad entre 31 aglomerados. "
        "3) El valor del gemelo se demostró al exponer ese baseline a E1, E2 y E3, con deltas diferenciados por canal. "
        "4) E1 evidencia retornos decrecientes de la sola conectividad; E2, sensibilidad educativa de la movilidad proxy; "
        "E3, efectos combinados más equilibrados. "
        "5) Quedó instalada infraestructura actualizable y pública en el Observatorio de Inteligencia Artificial. "
        "6) Los seis objetivos del Anexo I se cumplen al 100% en ejecución técnica y evidencia.",
    )
    add_lv(
        "Limitaciones del estudio: ",
        "Cobertura urbana de la EPH; calendario INDEC; escenarios no causales ni oficiales; restricciones de modelos ante cambios estructurales bruscos.",
    )
    add_lv(
        "Proyecciones futuras (2025–2030): ",
        "2025–2026: actualización periódica y ampliación de escenarios; difusión en jornadas UCCuyo. "
        "2027–2028: artículos académicos y convenios con áreas de gobierno. "
        "2029–2030: consolidación de la línea de gemelos digitales e IA aplicada a ciencias sociales.",
    )

    add_h("Impacto y proyección final")
    add_lv(
        "Relevancia académica y social: ",
        "GEMEPH aporta conocimiento metodológico original al combinar microdatos oficiales, representación territorial y simulación contrafactual. "
        "Socialmente, permite discutir políticas de conectividad, educación y formalización con números anclados en la EPH.",
    )
    add_lv(
        "Continuidad del proyecto: ",
        "La arquitectura modular incorpora nuevas ondas EPH sin rediseño. Continúa como línea del Observatorio de IA, "
        "con potencial de tesis, semilleros, convenios y actualizaciones según disponibilidad TIC.",
    )
    add_lv(
        "Valor agregado institucional: ",
        "La UCCuyo incorpora plataforma GEMEPH, pipelines, catálogo de 31 aglomerados, protocolos E1–E3, reportes automatizables y equipo formado, "
        "fortaleciendo investigación, docencia, extensión y vinculación tecnológica.",
    )

    add_h("Norma de citación", 2)
    add_p(
        "Se adopta la norma APA 7ª edición para referencias bibliográficas y menciones en el cuerpo del informe.",
        align="justify",
    )

    add_h("Bibliografía", 2)
    refs = [
        "Batty, M. (2024). The future of digital twins. Environment and Planning B: Urban Analytics and City Science.",
        "Fuller, A., Fan, Z., Day, C., & Barlow, C. (2020). Digital twin: Enabling technologies, challenges and open research. IEEE Access, 8, 108952–108971. https://doi.org/10.1109/ACCESS.2020.2998358",
        "Instituto Nacional de Estadística y Censos [INDEC]. (2024). Encuesta Permanente de Hogares (EPH): Bases de microdatos y metodología. https://www.indec.gob.ar",
        "Jones, D., Snider, C., Nassehi, A., Yon, J., & Hicks, B. (2020). Characterising the Digital Twin: A systematic literature review. CIRP Journal of Manufacturing Science and Technology, 29, 36–52.",
        "Organisation for Economic Co-operation and Development [OECD]. (2024). OECD digital economy outlook 2024. OECD Publishing.",
        "Rasheed, A., San, O., & Kvamsdal, T. (2020). Digital twin: Values, challenges and enablers from a modeling perspective. IEEE Access, 8, 21980–22012.",
        "UNESCO. (2021). Recommendation on the ethics of artificial intelligence. UNESCO.",
        "VanDerHorn, E., & Mahadevan, S. (2021). Digital twin: Generalization, characterization and implementation. Decision Support Systems, 145, 113524.",
    ]
    for ref in refs:
        add_p(ref, hanging=True, space_after=4)

    add_p("")
    add_h("Firma del Director/a", 2)
    add_lv("Firma y aclaración: ", "Claudio Marcelo Larrea Arnau")
    add_lv(
        "Unidad Académica: ",
        "Observatorio de Inteligencia Artificial — Universidad Católica de Cuyo",
    )
    add_lv("Equipo de investigación: ", "José La Malfa; Javier Coria; Stefania Young; Laura Pizarro")
    add_lv("Fecha: ", "21 de agosto de 2026")

    tmp = Path("/tmp/Anexo_III_GEMEPH_CS.docx")
    doc.save(str(tmp))
    targets = [
        OUT / "Anexo_III_Informe_Final_GEMEPH.docx",
        OUT / "01_Proyecto_investigacion" / "Anexo_III_Informe_Final_GEMEPH.docx",
        Path("/Users/claudiolarrea/Downloads/Anexo_III_Informe_Final_GEMEPH.docx"),
    ]
    for t in targets:
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tmp, t)
        print("SAVED", t)

    doc2 = Document(str(targets[0]))
    words = sum(len(p.text.split()) for p in doc2.paragraphs)
    print("words≈", words, "paras", len(doc2.paragraphs), "tables", len(doc2.tables))


if __name__ == "__main__":
    main()
