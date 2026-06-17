# -*- coding: utf-8 -*-
"""Descarga automática de microdatos INDEC (EPH + TIC) y reportes Excel/Word."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg")

import pandas as pd
import plotly.express as px
import streamlit as st

from indec_auto.src.analyze import ejecutar_analisis
from indec_auto.src.config import ANALISIS_DISPONIBLES, YEAR_MAX, YEAR_MIN
from indec_auto.src.download import available_years, download_panel
from indec_auto.src.prepare import build_analysis_frame, validate_microdata
from indec_auto.src.report import exportar_excel_bytes, exportar_word_bytes
from indec_auto.src.request import SolicitudAnalisis

CHART_COLORS = ["#1f4e79", "#2e7d32", "#c62828", "#6a1b9a"]

st.set_page_config(page_title="Microdatos INDEC automático", layout="wide")

ANALISIS_UI = [a for a in ANALISIS_DISPONIBLES if a != "todos"]

st.title("Microdatos INDEC automático")
st.markdown(
    "Descarga microdatos EPH (hogar, individuo y módulo TIC/MAUTIC) desde repositorios públicos "
    "y genera reportes en Excel y Word."
)
st.caption("Fuente: INDEC — EPH. Podés elegir módulo base (demográfico) o módulo con variables TIC.")


@st.cache_data(show_spinner="Descargando microdatos INDEC (hogar + individuo)…", ttl=86400)
def cargar_microdatos(years: tuple[int, ...], trimestre: int, force: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    hogar, individual = download_panel(
        years=list(years),
        trimester=trimestre,
        force=force,
    )
    return hogar, individual


@st.cache_data(show_spinner=False, ttl=86400)
def anios_disponibles_remoto(trimestre: int) -> list[int]:
    try:
        # Posicional para evitar incompatibilidades de firma entre versiones desplegadas.
        return available_years(trimestre, YEAR_MIN, YEAR_MAX)
    except Exception:
        return []


def _construir_solicitud() -> tuple[bool, SolicitudAnalisis]:
    with st.sidebar:
        st.subheader("Pedido de análisis")
        titulo = st.text_input("Título del informe", "Análisis EPH — inclusión digital y movilidad social")
        modulo = st.selectbox(
            "Módulo",
            options=["tic", "base"],
            format_func=lambda x: "Hogar + Individuo + TIC (variables digitales)" if x == "tic" else "Hogar + Individuo base (sociodemográfico)",
        )
        ambito = st.selectbox(
            "Ámbito geográfico",
            options=["nacional", "san_juan", "aglomerado"],
            format_func=lambda x: {
                "nacional": "Argentina (31 aglomerados)",
                "san_juan": "Gran San Juan",
                "aglomerado": "Aglomerado EPH (código)",
            }[x],
        )
        aglomerado = None
        if ambito == "aglomerado":
            aglomerado = st.number_input("Código aglomerado INDEC", min_value=1, max_value=99, value=27)

        year_mode = st.radio("Selección de años", ["Un año", "Rango"], horizontal=True)
        if year_mode == "Un año":
            year_single = st.number_input("Año", min_value=YEAR_MIN, max_value=YEAR_MAX, value=YEAR_MAX, step=1)
            years = [int(year_single)]
        else:
            y_min = st.number_input("Desde", min_value=YEAR_MIN, max_value=YEAR_MAX, value=max(YEAR_MIN, YEAR_MAX - 4), step=1)
            y_max = st.number_input("Hasta", min_value=YEAR_MIN, max_value=YEAR_MAX, value=YEAR_MAX, step=1)
            if y_min > y_max:
                st.warning("Ajusto el rango porque 'Desde' es mayor que 'Hasta'.")
                y_min, y_max = y_max, y_min
            years = list(range(int(y_min), int(y_max) + 1))

        trimestre_default = 4 if modulo == "tic" else 1
        trimestre = st.selectbox("Trimestre", [1, 2, 3, 4], index=trimestre_default - 1)
        if modulo == "tic" and trimestre != 4:
            st.info("Para TIC, normalmente corresponde usar T4.")

        anios_disponibles = anios_disponibles_remoto(trimestre)
        if anios_disponibles:
            st.caption(
                f"Años disponibles en fuente automática para T{trimestre}: "
                f"{anios_disponibles[0]}–{anios_disponibles[-1]}"
            )

        st.markdown("**Análisis a incluir**")
        todos = st.checkbox("Todos los análisis", value=False)
        if todos:
            analisis = ["todos"]
        else:
            analisis = st.multiselect(
                "Seleccionar",
                ANALISIS_UI,
                default=["descriptivos", "correlaciones"],
            )

        fmt_excel = st.checkbox("Generar Excel", value=True)
        fmt_word = st.checkbox("Generar Word", value=True)
        force = st.checkbox("Forzar nueva descarga", value=False)

        ejecutar = st.button("Ejecutar análisis", type="primary", use_container_width=True)

    return ejecutar, SolicitudAnalisis(
        titulo=titulo,
        years=years,
        trimestre=trimestre,
        modulo=modulo,
        ambito=ambito,
        aglomerado=int(aglomerado) if aglomerado is not None else None,
        analisis=analisis if analisis else ["todos"],
        excel=fmt_excel,
        word=fmt_word,
        force_download=force,
    )


ejecutar, solicitud = _construir_solicitud()

if ejecutar:
    with st.status("Procesando solicitud…", expanded=True) as status:
        st.write(f"Ámbito: **{solicitud.label}** · Período: **{solicitud.periodo_texto()}**")
        disponibles = anios_disponibles_remoto(solicitud.trimestre)
        faltantes = [y for y in solicitud.years if y not in disponibles]
        if faltantes:
            status.update(label="Solicitud con años no disponibles en fuente automática", state="error")
            st.error(
                "La fuente automática todavía no publica algunos años solicitados: "
                f"{', '.join(map(str, faltantes))}. "
                "Probá con años disponibles o usá la app manual para carga local."
            )
            st.stop()

        try:
            hogar, individual = cargar_microdatos(
                tuple(solicitud.years),
                solicitud.trimestre,
                solicitud.force_download,
            )
        except Exception as exc:
            status.update(label="Error al descargar microdatos", state="error")
            st.error(
                "No pude descargar los microdatos automáticamente desde la fuente pública.\n\n"
                f"Detalle: {exc}"
            )
            st.stop()
        df = build_analysis_frame(
            hogar,
            individual,
            aglomerado=solicitud.aglomerado_filtro,
            include_tic=(solicitud.modulo == "tic"),
        )
        val = validate_microdata(df)
        st.write(f"Registros analizados: **{len(df):,}**")
        st.json(val)

        resultado = ejecutar_analisis(
            df,
            tipos=solicitud.analisis_resueltos,
            label=solicitud.label,
        )
        resultado["meta"] = {
            "titulo": solicitud.titulo,
            "ambito": solicitud.label,
            "periodo": solicitud.periodo_texto(),
            "registros": len(df),
            "validacion": val,
            "modulo": solicitud.modulo,
            "fuente": "INDEC — EPH (hogar + individuo, con/sin TIC según selección)",
        }
        st.session_state["indec_resultado"] = resultado
        st.session_state["indec_solicitud"] = solicitud
        status.update(label="Análisis completado", state="complete")

resultado = st.session_state.get("indec_resultado")
solicitud_guardada: SolicitudAnalisis | None = st.session_state.get("indec_solicitud")

if resultado and solicitud_guardada:
    tablas = resultado.get("tablas", {})
    corr = resultado.get("correlacion_destacada")
    corr_txt = f"{corr:.3f}" if isinstance(corr, (float, int)) else "N/D"
    st.success(f"Resultados listos — {resultado['meta'].get('registros', 0):,} registros · correlación exclusión↔movilidad: {corr_txt}")

    c1, c2, c3 = st.columns(3)
    slug = solicitud_guardada.label
    if solicitud_guardada.excel:
        c1.download_button(
            "Descargar Excel",
            data=exportar_excel_bytes(resultado),
            file_name=f"reporte_eph_{slug}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    if solicitud_guardada.word:
        c2.download_button(
            "Descargar Word",
            data=exportar_word_bytes(
                resultado,
                titulo=solicitud_guardada.titulo,
                periodo=solicitud_guardada.periodo_texto(),
                ambito=solicitud_guardada.label,
            ),
            file_name=f"informe_eph_{slug}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )

    graf = resultado.get("grafico_shap")
    if graf and Path(graf).exists():
        c3.image(graf, caption="Importancia SHAP / evolución")

    desc = tablas.get("descriptivos_anuales")
    if desc is not None and not desc.empty:
        st.subheader("Evolución anual")
        y_cols = [c for c in ["idx_exclusion_digital", "score_movilidad_proxy", "vulnerabilidad_social"] if c in desc.columns]
        fig = px.line(
            desc,
            x="anio",
            y=y_cols,
            markers=True,
            color_discrete_sequence=CHART_COLORS[:2],
            labels={"value": "Índice", "anio": "Año", "variable": "Indicador"},
        )
        fig.update_layout(
            template="plotly_white",
            title="Exclusión digital y movilidad social (proxy)",
            legend_title_text="Indicador",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(desc, use_container_width=True, hide_index=True)
