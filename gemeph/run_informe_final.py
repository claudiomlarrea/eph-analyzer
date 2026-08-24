#!/usr/bin/env python3
"""Ejecuta GEMEPH (INDEC/EPH) y genera Excel, Word e Informe Final (Anexo III)."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from docx import Document
from docx.shared import Pt

from gemeph.baseline import build_baseline
from gemeph.catalog import build_catalog, catalog_to_dataframe, persist_gemeph_run
from gemeph.export import export_catalog_excel_bytes, export_word_bytes
from gemeph.panel import load_or_build_panel, periodo_texto
from gemeph.scenario import compare_rows, lever_baselines, run_scenario
from indec_auto.src.prepare import validate_microdata

OUT_DEFAULT = Path(
    "/Users/claudiolarrea/Library/CloudStorage/OneDrive-Personal/11 Investigacion/2026/GEMEPH"
)
TEMPLATE_ANEXO_III = Path(
    "/Users/claudiolarrea/Downloads/3 Anexo III. Presentación de informes finales.docx"
)


def _fmt(v: Any, nd: int = 4) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    if isinstance(v, (int,)):
        return f"{v:,}".replace(",", ".")
    return str(v)


def _set_para_text(paragraph, text: str) -> None:
    if paragraph.runs:
        paragraph.runs[0].text = text
        for r in paragraph.runs[1:]:
            r.text = ""
    else:
        paragraph.add_run(text)


def _replace_in_doc(doc: Document, mapping: dict[str, str]) -> None:
    """Reemplaza marcadores exactos o rellena párrafos plantilla por prefijo."""
    for p in doc.paragraphs:
        t = p.text
        for old, new in mapping.items():
            if old in t:
                _set_para_text(p, t.replace(old, new))
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    t = p.text
                    for old, new in mapping.items():
                        if old in t:
                            _set_para_text(p, t.replace(old, new))


def _delete_recomendaciones(doc: Document) -> None:
    from docx.oxml.ns import qn

    to_remove = []
    skip = False
    for p in doc.paragraphs:
        t = p.text.strip()
        if t.startswith("Recomendaciones") or t == "Agregar:" or t.startswith("Recomendaciones finales"):
            skip = True
            to_remove.append(p)
            continue
        if skip:
            if t.startswith("Sección") or t.startswith("Conclusiones") or t.startswith("Impacto") or t.startswith("Firma") or t.startswith("Artículos") or t.startswith("Metodología") or t.startswith("Resultados") or t.startswith("Síntesis") or t.startswith("Ejecución") or t.startswith("Denominación") or t.startswith("Calidad") or t.startswith("Tener en cuenta"):
                skip = False
            elif t.startswith("•") or t.startswith("300 palabras") or t.startswith("Declaración") or not t:
                to_remove.append(p)
                continue
            else:
                skip = False
    for p in to_remove:
        el = p._element
        parent = el.getparent()
        if parent is not None:
            parent.remove(el)


def build_rich_excel(
    cat_df: pd.DataFrame,
    baseline: dict[str, Any],
    scenario: dict[str, Any],
    meta: dict[str, Any],
    val: dict[str, Any],
) -> bytes:
    import io

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame([{"campo": k, "valor": str(v)} for k, v in meta.items()]).to_excel(
            writer, sheet_name="metadatos", index=False
        )
        pd.DataFrame([{"campo": k, "valor": str(v)} for k, v in val.items()]).to_excel(
            writer, sheet_name="validacion_datos", index=False
        )
        cat_df.to_excel(writer, sheet_name="catalogo_31_aglomerados", index=False)
        aglo = cat_df.loc[cat_df["tipo"] == "aglomerado"].copy()
        if not aglo.empty and "idx_exclusion_digital" in aglo.columns:
            aglo.sort_values("idx_exclusion_digital", ascending=False).to_excel(
                writer, sheet_name="ranking_exclusion_digital", index=False
            )
            if "vulnerabilidad_social" in aglo.columns:
                aglo.sort_values("vulnerabilidad_social", ascending=False).head(15).to_excel(
                    writer, sheet_name="top_vulnerabilidad", index=False
                )
        kpis = dict(baseline.get("kpis", {}))
        brechas = kpis.pop("brechas", {}) if isinstance(kpis.get("brechas"), dict) else {}
        flat = {**kpis, **{f"brecha_{k}": v for k, v in brechas.items()}}
        pd.DataFrame([flat]).to_excel(writer, sheet_name="baseline_nacional", index=False)
        if baseline.get("evolucion"):
            pd.DataFrame(baseline["evolucion"]).to_excel(writer, sheet_name="evolucion", index=False)
        if baseline.get("perfiles"):
            pd.DataFrame(baseline["perfiles"]).to_excel(writer, sheet_name="perfiles_cluster", index=False)
        cmp = compare_rows(scenario)
        cmp.to_excel(writer, sheet_name="escenario_what_if", index=False)
        pd.DataFrame([scenario.get("modelo", {})]).to_excel(writer, sheet_name="modelo_predictivo", index=False)
        pd.DataFrame([scenario.get("targets", {})]).to_excel(writer, sheet_name="palancas_escenario", index=False)
        # Hallazgos OE
        hallazgos = _hallazgos_rows(cat_df, baseline, scenario, meta)
        pd.DataFrame(hallazgos).to_excel(writer, sheet_name="hallazgos_OE1_OE6", index=False)
    buf.seek(0)
    return buf.getvalue()


def _hallazgos_rows(
    cat_df: pd.DataFrame,
    baseline: dict[str, Any],
    scenario: dict[str, Any],
    meta: dict[str, Any],
) -> list[dict[str, Any]]:
    nac = cat_df.loc[cat_df["territorio_id"] == "nacional"]
    row = nac.iloc[0] if not nac.empty else {}
    aglo = cat_df.loc[cat_df["tipo"] == "aglomerado"]
    top_exc = ""
    top_vuln = ""
    if not aglo.empty and "idx_exclusion_digital" in aglo.columns:
        t = aglo.nlargest(3, "idx_exclusion_digital")
        top_exc = "; ".join(f"{r.territorio_nombre}={r.idx_exclusion_digital:.3f}" for r in t.itertuples())
    if not aglo.empty and "vulnerabilidad_social" in aglo.columns:
        t = aglo.nlargest(3, "vulnerabilidad_social")
        top_vuln = "; ".join(f"{r.territorio_nombre}={r.vulnerabilidad_social:.3f}" for r in t.itertuples())
    modelo = scenario.get("modelo", {})
    return [
        {"OE": "OE1", "hallazgo": "Arquitectura GEMEPH operativa: panel maestro, catálogo de 31 aglomerados + nacional, baselines y escenarios what-if.", "evidencia": meta.get("plataforma", "")},
        {"OE": "OE2", "hallazgo": f"Base EPH integrada y validada. Registros panel: {meta.get('registros_panel')}. Período: {meta.get('periodo')}.", "evidencia": f"n_territorios={meta.get('n_territorios')}"},
        {"OE": "OE3", "hallazgo": "Modelos IA/ML: clústeres sociodigitales + regresión logística de exclusión digital alta con simulación contrafactual.", "evidencia": f"pred_base={modelo.get('pct_exclusion_predicho_base')}% → pred_esc={modelo.get('pct_exclusion_predicho_escenario')}%"},
        {"OE": "OE4", "hallazgo": "Plataforma interactiva publicada con mapa, comparación, evolución y escenarios.", "evidencia": "https://eph-analyzer.streamlit.app/GEMEPH"},
        {"OE": "OE5", "hallazgo": f"Validación: exclusión digital nacional={_fmt(row.get('idx_exclusion_digital'))}; vulnerabilidad={_fmt(row.get('vulnerabilidad_social'))}; movilidad proxy={_fmt(row.get('score_movilidad_proxy'))}.", "evidencia": f"Top exclusión: {top_exc}. Top vulnerabilidad: {top_vuln}"},
        {"OE": "OE6", "hallazgo": "Entregables: Excel resultados, Word ejecutivo, Anexo III Informe Final y repositorio reproducible.", "evidencia": "Carpeta GEMEPH / Observatorio IA UCCuyo"},
    ]


def fill_anexo_iii(
    template: Path,
    out_path: Path,
    *,
    cat_df: pd.DataFrame,
    baseline: dict[str, Any],
    scenario: dict[str, Any],
    meta: dict[str, Any],
    val: dict[str, Any],
) -> Path:
    doc = Document(str(template))
    _delete_recomendaciones(doc)

    nac = cat_df.loc[cat_df["territorio_id"] == "nacional"]
    row = nac.iloc[0] if not nac.empty else pd.Series(dtype=object)
    aglo = cat_df.loc[cat_df["tipo"] == "aglomerado"].copy()
    top5 = []
    if not aglo.empty and "idx_exclusion_digital" in aglo.columns:
        for r in aglo.nlargest(5, "idx_exclusion_digital").itertuples():
            top5.append(f"{r.territorio_nombre} ({r.idx_exclusion_digital:.4f})")
    cmp = compare_rows(scenario)
    esc_lines = []
    for _, r in cmp.iterrows():
        esc_lines.append(f"{r['Indicador']}: {_fmt(r['Baseline'])} → {_fmt(r['Escenario'])} (Δ {_fmt(r.get('Cambio'))})")
    modelo = scenario.get("modelo", {})
    perfiles = baseline.get("perfiles") or []
    perfiles_txt = "; ".join(f"{p.get('nombre')} ({p.get('pct')}%)" for p in perfiles) or "—"

    resumen = (
        f"El informe final del proyecto GEMEPH documenta el desarrollo y validación de un gemelo digital "
        f"sociodemográfico territorial basado en microdatos EPH-INDEC (módulo {meta.get('modulo')}, período {meta.get('periodo')}). "
        f"Se integró un panel maestro de {meta.get('registros_panel')} registros individuales y un catálogo de "
        f"{meta.get('n_territorios')} territorios (Argentina + 31 aglomerados urbanos). "
        f"A nivel nacional, el índice de exclusión digital es {_fmt(row.get('idx_exclusion_digital'))}, "
        f"la vulnerabilidad social {_fmt(row.get('vulnerabilidad_social'))}, la movilidad social proxy {_fmt(row.get('score_movilidad_proxy'))}, "
        f"la ocupación {_fmt(row.get('pct_ocupado'), 2)}% y la educación superior {_fmt(row.get('pct_superior'), 2)}%. "
        f"Los aglomerados con mayor exclusión digital son: {', '.join(top5)}. "
        f"Se implementaron perfiles sociodigitales por clúster ({perfiles_txt}) y un escenario what-if con modelo predictivo "
        f"(probabilidad de exclusión alta: {modelo.get('pct_exclusion_predicho_base')}% → {modelo.get('pct_exclusion_predicho_escenario')}%). "
        f"La plataforma interactiva está publicada en https://eph-analyzer.streamlit.app/GEMEPH, "
        f"habilitando consulta, comparación territorial, evolución y simulación para investigación y decisión."
    )

    metodologia = (
        "Diseño: investigación aplicada tecnológica (Design Science Research) con enfoque cuantitativo longitudinal. "
        f"Bases: microdatos públicos EPH-INDEC (hogar + individuo + TIC), período {meta.get('periodo')}. "
        "Variables: ocupación, educación, vulnerabilidad social, exclusión digital, brechas de género/ingreso, movilidad proxy. "
        "Herramientas: Python, pandas, scikit-learn, Streamlit, Plotly, GEMEPH (eph-analyzer). "
        f"Validación: control de calidad de microdatos ({json.dumps(val, ensure_ascii=False)[:280]}), "
        "métricas territoriales ponderadas, clústeres y modelo logístico de exclusión. "
        "Limitaciones: EPH urbana (31 aglomerados); dependencia de publicación INDEC; asociaciones no causales; "
        "escenarios contrafactuales no son proyecciones oficiales."
    )

    resultados = (
        f"Resultados nacionales (ponderados): exclusión digital={_fmt(row.get('idx_exclusion_digital'))}; "
        f"% exclusión alta={_fmt(row.get('pct_exclusion_digital_alta'), 2)}; "
        f"vulnerabilidad={_fmt(row.get('vulnerabilidad_social'))}; movilidad proxy={_fmt(row.get('score_movilidad_proxy'))}; "
        f"ocupación={_fmt(row.get('pct_ocupado'), 2)}%; superior={_fmt(row.get('pct_superior'), 2)}%. "
        f"Brechas territoriales: top exclusión digital = {'; '.join(top5)}. "
        f"Escenario what-if: " + " | ".join(esc_lines) + ". "
        "Discusión: GEMEPH demuestra que es posible pasar de análisis descriptivos aislados a una infraestructura "
        "de gemelo digital reproducible, con representación territorial, predicción y simulación sobre datos oficiales abiertos, "
        "alineada a los objetivos de exclusión digital, vulnerabilidad y brechas territoriales del proyecto."
    )

    # Fill by prefix matching empty template fields
    fills = [
        ("Título del Proyecto:", "Título del Proyecto: GEMEPH — Gemelo digital sociodemográfico de la EPH-INDEC: exclusión digital, vulnerabilidad y brechas territoriales en Argentina"),
        ("Director/a:", "Director/a: Claudio Marcelo Larrea Arnau"),
        ("Unidad Académica:", "Unidad Académica: Observatorio de Inteligencia Artificial — Universidad Católica de Cuyo"),
        ("Resolución de Aprobación Nº:", "Resolución de Aprobación Nº: (a completar por Secretaría)"),
        ("Período Informado:", f"Período Informado: {meta.get('periodo')} (microdatos EPH-INDEC)"),
        ("Fecha de Presentación:", f"Fecha de Presentación: {datetime.now().strftime('%d de %B de %Y')}".replace("August", "agosto")),
        ("Denominación del Proyecto:", "Denominación del Proyecto: GEMEPH: Desarrollo y validación de un Gemelo Digital Sociodemográfico Territorial basado en la EPH-INDEC"),
        ("Equipo de trabajo:", "Equipo de trabajo: Claudio Marcelo Larrea Arnau (Director); José La Malfa (Co-director); Javier Coria; Stefania Young"),
        ("Fuente de financiamiento:", "Fuente de financiamiento: Interna (UCCuyo / Observatorio de Inteligencia Artificial)"),
        ("Duración del Proyecto:", "Duración del Proyecto: 12 meses"),
        ("Período informado:", f"Período informado: {meta.get('periodo')}"),
        ("Presupuesto total asignado:", "Presupuesto total asignado: $0"),
        ("Presupuesto ejecutado:", "Presupuesto ejecutado: $0"),
        ("Porcentaje de ejecución:", "Porcentaje de ejecución: 100% (sin fondos dinerarios; ejecución con recursos institucionales)"),
        ("Observaciones o rendición externa:", "Observaciones o rendición externa: No aplica."),
        ("Síntesis de los resultados más significativos (hasta 300 palabras):", "Síntesis de los resultados más significativos (hasta 300 palabras):\n" + resumen),
        ("Diseño del estudio:", "Diseño del estudio: " + metodologia.split("Bases:")[0].replace("Diseño: ", "")),
        ("Bases de datos y fuentes utilizadas:", f"Bases de datos y fuentes utilizadas: Microdatos EPH-INDEC (hogar, individuo y módulo TIC). Período {meta.get('periodo')}. Plataforma https://eph-analyzer.streamlit.app/GEMEPH"),
        ("Variables analizadas:", "Variables analizadas: ocupación, educación superior, informalidad, exclusión digital, vulnerabilidad social, movilidad social proxy, brechas de género e ingreso, perfiles por clúster."),
        ("Herramientas de análisis (software / IA / estadística):", "Herramientas de análisis (software / IA / estadística): Python, pandas, scikit-learn (clustering, regresión logística), Streamlit, Plotly, openpyxl, python-docx; módulo GEMEPH del sistema eph-analyzer."),
        ("Procedimientos de validación de resultados:", f"Procedimientos de validación de resultados: validación de microdatos, KPIs ponderados por PONDERA, comparación entre 31 aglomerados, clústeres sociodigitales y modelo predictivo de exclusión (base {modelo.get('pct_exclusion_predicho_base')}% vs escenario {modelo.get('pct_exclusion_predicho_escenario')}%)."),
        ("Limitaciones del estudio:", "Limitaciones del estudio: cobertura urbana EPH (31 aglomerados); periodicidad INDEC; no causalidad; escenarios contrafactuales no oficiales; heterogeneidad TIC entre trimestres."),
        ("Presentar los principales resultados cuantitativos y cualitativos, análisis comparativo y discusión crítica de los hallazgos.", "Resultados y discusión:\n" + resultados),
        ("Artículos publicados:", "Artículos publicados: En preparación a partir de resultados GEMEPH 2022–2024 / corrida vigente."),
        ("Ponencias y congresos:", "Ponencias y congresos: Previstas en Jornadas de Investigación UCCuyo y eventos de ciencia de datos / IA aplicada."),
        ("Productos tecnológicos (aplicaciones, tableros, informes):", "Productos tecnológicos: plataforma https://eph-analyzer.streamlit.app/GEMEPH; Excel de resultados territoriales; Word ejecutivo; pipelines reproducibles en repositorio eph-analyzer."),
        ("Formación de recursos humanos (tesis, becarios, estudiantes):", "Formación de recursos humanos: equipo José La Malfa, Javier Coria y Stefania Young en integración de datos, modelado y documentación."),
        ("Actividades de divulgación:", "Actividades de divulgación: tableros públicos GEMEPH, informes para Observatorio de IA y transferencia a organismos interesados."),
        ("Principales conclusiones:", "Principales conclusiones: 1) Se consolidó GEMEPH como gemelo digital sociodemográfico operativo sobre EPH-INDEC. 2) El catálogo de 31 aglomerados permite medir exclusión digital, vulnerabilidad y brechas territoriales de forma comparable. 3) Los modelos de IA/ML y escenarios what-if habilitan simulación para investigación y decisión. 4) Queda instalada una infraestructura actualizable con cada publicación de microdatos INDEC."),
        ("Limitaciones del estudio:", "Limitaciones del estudio: EPH urbana; dependencia de actualización INDEC; interpretaciones no causales; escenarios contrafactuales."),
        ("Proyecciones futuras (2025–2030):", "Proyecciones futuras (2025–2030): actualización trimestral/anual del gemelo; artículo académico; ampliación de palancas de simulación; articulación con organismos públicos y consolidación de la línea institucional en gemelos digitales."),
        ("Firma y aclaración:", "Firma y aclaración: Claudio Marcelo Larrea Arnau"),
        ("Unidad Académica:", "Unidad Académica: Observatorio de Inteligencia Artificial — Universidad Católica de Cuyo"),
        ("Fecha:", f"Fecha: {datetime.now().strftime('%d/%m/%Y')}"),
    ]

    # Apply fills: for paragraphs that start with label or equal label
    for p in doc.paragraphs:
        raw = p.text
        stripped = raw.strip()
        for label, full in fills:
            if stripped == label or stripped.startswith(label):
                # avoid double-filling Unidad Académica / Limitaciones / Fecha multiple times carefully
                _set_para_text(p, full)
                break

    # Cronograma table OE1-OE6
    if doc.tables:
        table = doc.tables[0]
        rows_data = [
            ("OE1. Arquitectura conceptual/metodológica/tecnológica", "Diseño de componentes, datos y actualización", "Arquitectura GEMEPH implementada (panel, catálogo, baselines, escenarios)", "100%", "App GEMEPH + código eph-analyzer", "Sin desvíos"),
            ("OE2. Integración y normalización EPH", "ETL microdatos INDEC", f"Panel integrado ({meta.get('registros_panel')} registros) validado", "100%", "Parquet/panel + hoja validacion_datos", "Actualizable con nuevas bases"),
            ("OE3. Modelos IA/ML y simulación", "Clustering, predicción, escenarios", "Clústeres + modelo logístico + what-if ejecutados", "100%", "Hojas perfiles_cluster / escenario_what_if", "—"),
            ("OE4. Plataforma interactiva", "Visualización, consulta y simulación", "Publicada en Streamlit Cloud", "100%", "https://eph-analyzer.streamlit.app/GEMEPH", "—"),
            ("OE5. Validación técnico-científica", "Calidad, predictividad, utilidad", "KPIs nacionales y ranking de 31 aglomerados validados", "100%", "Excel ranking_exclusion_digital", "—"),
            ("OE6. Documentación y transferencia", "Informes, publicaciones, productos", "Excel, Word e Informe Final Anexo III entregados", "100%", "Carpeta GEMEPH", "Publicaciones en curso"),
        ]
        # Ensure rows
        while len(table.rows) < 7:
            table.add_row()
        headers = ["Objetivo específico", "Actividades planificadas", "Actividades ejecutadas", "% de avance", "Evidencias / entregables", "Comentarios / desvíos"]
        for c, h in enumerate(headers):
            if c < len(table.rows[0].cells):
                table.rows[0].cells[c].text = h
        for i, data in enumerate(rows_data, start=1):
            if i >= len(table.rows):
                break
            for c, val in enumerate(data):
                if c < len(table.rows[i].cells):
                    table.rows[i].cells[c].text = val

    # Append impact + bibliography if missing substantial content
    # Add closing sections as new paras before firma if needed
    from docx.oxml import OxmlElement
    from docx.text.paragraph import Paragraph

    firma = None
    for p in doc.paragraphs:
        if p.text.strip().startswith("Firma del Director"):
            firma = p
            break
    if firma is not None:
        extras = [
            ("Impacto y proyección final", True),
            (
                "Relevancia académica y social: GEMEPH aporta una infraestructura inédita de gemelo digital sobre EPH para analizar exclusión digital, vulnerabilidad y brechas territoriales con evidencia reproducible.",
                False,
            ),
            (
                "Continuidad del proyecto: actualización con cada liberación de microdatos INDEC; ampliación de escenarios y publicaciones 2025–2030.",
                False,
            ),
            (
                "Valor agregado institucional: plataforma, pipelines, catálogo territorial y capacidad de formación en IA aplicada instalados en el Observatorio de Inteligencia Artificial.",
                False,
            ),
            ("Norma de citación: APA 7ª edición.", False),
            ("Bibliografía (selección)", True),
            ("Fuller, A., Fan, Z., Day, C., & Barlow, C. (2020). Digital twin: Enabling technologies, challenges and open research. IEEE Access, 8, 108952–108971.", False),
            ("Instituto Nacional de Estadística y Censos [INDEC]. (2024). Encuesta Permanente de Hogares (EPH). https://www.indec.gob.ar", False),
            ("UNESCO. (2021). Recommendation on the ethics of artificial intelligence. UNESCO.", False),
            ("Batty, M. (2024). The future of digital twins. Environment and Planning B: Urban Analytics and City Science.", False),
        ]
        # insert before firma in reverse
        for text, bold in reversed(extras):
            new_p = OxmlElement("w:p")
            firma._p.addprevious(new_p)
            para = Paragraph(new_p, firma._parent)
            run = para.add_run(text)
            run.bold = bold
            run.font.size = Pt(11)

    # Fix fecha presentation language
    for p in doc.paragraphs:
        if "Fecha de Presentación:" in p.text and "August" in p.text:
            _set_para_text(p, f"Fecha de Presentación: {datetime.now().strftime('%d/%m/%Y')}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    return out_path


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2022-2024", help="Año o rango, ej. 2024 o 2022-2024")
    ap.add_argument("--trimestre", type=int, default=4)
    ap.add_argument("--modulo", choices=["tic", "base"], default="tic")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    if "-" in args.years:
        y0, y1 = map(int, args.years.split("-", 1))
        years = list(range(y0, y1 + 1))
    else:
        years = [int(args.years)]

    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    results_dir = out_dir / "02_Resultados_empiricos"
    results_dir.mkdir(parents=True, exist_ok=True)

    print("==> Construyendo panel GEMEPH…")
    panel, val_cache, run_id = load_or_build_panel(
        years, args.trimestre, modulo=args.modulo, force_download=args.force
    )
    val = validate_microdata(panel)
    val.update({k: v for k, v in val_cache.items() if k not in val})
    periodo = periodo_texto(years, args.trimestre)
    print(f"    run_id={run_id} n={len(panel):,} periodo={periodo}")

    print("==> Persistiendo catálogo y baselines…")
    persist_gemeph_run(panel, run_id=run_id, periodo=periodo, modulo=args.modulo, save_panel_parquet=True)

    catalog = build_catalog(panel, periodo=periodo, modulo=args.modulo)
    cat_df = catalog_to_dataframe(catalog)
    baseline = build_baseline(panel, "nacional", periodo=periodo, modulo=args.modulo, include_clusters=True)

    print("==> Escenario what-if…")
    levers = lever_baselines(panel, include_tic=(args.modulo == "tic"))
    # Mejora moderada: conectividad Q1, educación superior y formalidad laboral
    targets: dict[str, float] = {}
    if levers.get("internet_quintil_i") is not None:
        targets["internet_quintil_i"] = min(99.0, float(levers["internet_quintil_i"]) + 10.0)
    if levers.get("pct_superior") is not None:
        targets["pct_superior"] = min(99.0, float(levers["pct_superior"]) + 5.0)
    if levers.get("pct_empleo_formal") is not None:
        targets["pct_empleo_formal"] = min(99.0, float(levers["pct_empleo_formal"]) + 5.0)
    print("    levers=", levers, "targets=", targets)
    scenario = run_scenario(panel, targets, include_tic=(args.modulo == "tic"))

    meta = {
        "titulo": "GEMEPH — Gemelo digital sociodemográfico EPH-INDEC",
        "periodo": periodo,
        "modulo": args.modulo,
        "run_id": run_id,
        "fuente": "INDEC — EPH (hogar + individuo + TIC)",
        "registros_panel": len(panel),
        "n_territorios": int(catalog.get("n_territorios", 0)),
        "plataforma": "https://eph-analyzer.streamlit.app/GEMEPH",
        "generado": datetime.now().isoformat(timespec="seconds"),
        "director": "Claudio Marcelo Larrea Arnau",
        "unidad": "Observatorio de Inteligencia Artificial — UCCuyo",
    }

    stamp = datetime.now().strftime("%Y%m%d")
    excel_path = results_dir / f"GEMEPH_resultados_{run_id}_{stamp}.xlsx"
    word_path = results_dir / f"GEMEPH_informe_resultados_{run_id}_{stamp}.docx"
    anexo_path = out_dir / "01_Proyecto_investigacion" / "Anexo_III_Informe_Final_GEMEPH.docx"
    anexo_path.parent.mkdir(parents=True, exist_ok=True)
    resumen_json = results_dir / f"GEMEPH_resumen_{run_id}_{stamp}.json"

    print("==> Excel…")
    excel_path.write_bytes(build_rich_excel(cat_df, baseline, scenario, meta, val))

    print("==> Word resultados…")
    word_path.write_bytes(
        export_word_bytes(
            titulo=meta["titulo"],
            periodo=periodo,
            cat_df=cat_df,
            baseline=baseline,
            scenario=scenario,
        )
    )

    print("==> Anexo III…")
    if not TEMPLATE_ANEXO_III.exists():
        raise FileNotFoundError(TEMPLATE_ANEXO_III)
    fill_anexo_iii(
        TEMPLATE_ANEXO_III,
        anexo_path,
        cat_df=cat_df,
        baseline=baseline,
        scenario=scenario,
        meta=meta,
        val=val,
    )
    # Mirror copies
    anexo_copy = out_dir / "Anexo_III_Informe_Final_GEMEPH.docx"
    anexo_copy.write_bytes(anexo_path.read_bytes())
    excel_copy = out_dir / excel_path.name
    word_copy = out_dir / word_path.name
    excel_copy.write_bytes(excel_path.read_bytes())
    word_copy.write_bytes(word_path.read_bytes())

    payload = {
        "meta": meta,
        "validacion": val,
        "baseline_kpis": baseline.get("kpis"),
        "perfiles": baseline.get("perfiles"),
        "scenario_deltas": scenario.get("deltas"),
        "scenario_modelo": scenario.get("modelo"),
        "archivos": {
            "excel": str(excel_path),
            "word": str(word_path),
            "anexo_iii": str(anexo_path),
        },
    }
    resumen_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    print("LISTO")
    print("Excel:", excel_path)
    print("Word:", word_path)
    print("Anexo III:", anexo_path)
    nac = cat_df.loc[cat_df["territorio_id"] == "nacional"]
    if not nac.empty:
        r = nac.iloc[0]
        print(
            "Nacional:",
            f"excl={r.get('idx_exclusion_digital')}",
            f"vuln={r.get('vulnerabilidad_social')}",
            f"mov={r.get('score_movilidad_proxy')}",
        )


if __name__ == "__main__":
    main()
