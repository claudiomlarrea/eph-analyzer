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

from indec_auto.src.aglomerados import opciones_aglomerado_ui
from indec_auto.src.analyze import ejecutar_analisis
from indec_auto.src.config import (
    ANALISIS_DISPONIBLES,
    PROYECTO_CUYO_TITULO,
    PROYECTO_CUYO_TRIMESTRE,
    PROYECTO_CUYO_YEAR_MAX,
    PROYECTO_CUYO_YEAR_MIN,
    YEAR_MAX,
    YEAR_MIN,
)
from indec_auto.src.download import available_years, download_panel
from indec_auto.src.prepare import build_analysis_frame, validate_microdata
from indec_auto.src.proyecto_cuyo import (
    anios_proyecto_disponibles,
    ejecutar_proyecto_cuyo,
    periodos_proyecto_disponibles,
)from indec_auto.src.report import exportar_excel_bytes, exportar_word_bytes, resumen_interpretacion_indices
from indec_auto.src.request import SolicitudAnalisis
from src.etiquetador import nombre_completo

CHART_COLORS = ["#1f4e79", "#2e7d32", "#c62828", "#6a1b9a"]

st.set_page_config(page_title="Microdatos INDEC automático", layout="wide")

ANALISIS_UI = [a for a in ANALISIS_DISPONIBLES if a != "todos"]

st.title("Microdatos INDEC automático")
st.markdown(
    "Descarga microdatos EPH (hogar, individuo y módulo TIC/MAUTIC) desde repositorios públicos "
    "y genera reportes en Excel y Word."
)
st.caption(
    "Fuente automática: mirror GitHub + INDEC oficial (fallback). "
    "Podés elegir módulo base (demográfico) o módulo con variables TIC."
)


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
        return available_years(trimestre, YEAR_MIN, YEAR_MAX)
    except Exception:
        return []


@st.cache_data(show_spinner=False, ttl=3600)
def anios_proyecto_cache(trimestre: int) -> list[int]:
    try:
        return anios_proyecto_disponibles(trimestre)
    except Exception:
        return []


@st.cache_data(show_spinner=False, ttl=3600)
def periodos_proyecto_cache() -> list[tuple[int, int]]:
    try:
        return periodos_proyecto_disponibles()
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Modo Proyecto Cuyo (one-click)
# ---------------------------------------------------------------------------
st.header("Proyecto Cuyo — un clic")
st.markdown(
    f"**{PROYECTO_CUYO_TITULO}**  \n"
    "Descarga microdatos INDEC de **todos los trimestres disponibles (2024–2026)**, "
    "analiza Nación + Gran Cuyo + Mendoza + San Luis + San Juan, y genera los resultados "
    "de la observación empírica alineados a los objetivos del proyecto (ejecución 2025–2026)."
)

periodos_proy = periodos_proyecto_cache()
if periodos_proy:
    st.info(
        f"Períodos detectados: **{len(periodos_proy)}** "
        f"({periodos_proy[0][0]}T{periodos_proy[0][1]} … "
        f"{periodos_proy[-1][0]}T{periodos_proy[-1][1]})."
    )
else:
    st.warning(
        f"No se detectaron períodos {PROYECTO_CUYO_YEAR_MIN}–{PROYECTO_CUYO_YEAR_MAX}. "
        "Podés forzar descarga o usar el modo manual abajo."
    )

c_force, c_run = st.columns([1, 2])
with c_force:
    force_proyecto = st.checkbox("Forzar nueva descarga (proyecto)", value=False, key="force_proyecto_cuyo")
with c_run:
    ejecutar_proyecto = st.button(
        "▶ Ejecutar proyecto Cuyo (INDEC → resultados por objetivo)",
        type="primary",
        use_container_width=True,
    )

if ejecutar_proyecto:
    with st.status("Ejecutando proyecto Cuyo…", expanded=True) as status:
        logs: list[str] = []

        def _progress(msg: str) -> None:
            logs.append(msg)
            st.write(msg)

        try:
            resultado = ejecutar_proyecto_cuyo(
                periodos=periodos_proy or None,
                force_download=force_proyecto,
                titulo=PROYECTO_CUYO_TITULO,
                progress=_progress,
            )
        except Exception as exc:
            status.update(label="Error en proyecto Cuyo", state="error")
            st.error(f"No pude completar el proyecto automáticamente.\n\nDetalle: {exc}")
            st.stop()

        st.session_state["indec_resultado"] = resultado
        st.session_state["indec_solicitud"] = SolicitudAnalisis(
            titulo=PROYECTO_CUYO_TITULO,
            years=resultado["meta"].get("anios", [PROYECTO_CUYO_YEAR_MIN, PROYECTO_CUYO_YEAR_MAX]),
            trimestre=PROYECTO_CUYO_TRIMESTRE,
            modulo="tic",
            ambito="cuyo",
            analisis=["todos"],
            excel=True,
            word=True,
            force_download=force_proyecto,
        )
        st.session_state["modo_proyecto_cuyo"] = True
        status.update(label="Proyecto Cuyo completado", state="complete")


def _construir_solicitud() -> tuple[bool, SolicitudAnalisis]:
    with st.sidebar:
        st.subheader("Pedido de análisis")
        st.caption("Modo manual (si no usás el botón Proyecto Cuyo).")
        titulo = st.text_input("Título del informe", PROYECTO_CUYO_TITULO)
        modulo = st.selectbox(
            "Módulo",
            options=["tic", "base"],
            format_func=lambda x: (
                "Hogar + Individuo + TIC (variables digitales)"
                if x == "tic"
                else "Hogar + Individuo base (sociodemográfico)"
            ),
        )
        ambito = st.selectbox(
            "Ámbito geográfico",
            options=["nacional", "cuyo", "san_juan", "aglomerado"],
            format_func=lambda x: {
                "nacional": "Argentina (todos los aglomerados)",
                "cuyo": "Gran Cuyo (Mendoza + San Luis + San Juan)",
                "san_juan": "Gran San Juan",
                "aglomerado": "Aglomerado EPH",
            }[x],
        )
        aglomerado = None
        if ambito == "aglomerado":
            opciones = opciones_aglomerado_ui()
            etiquetas = [etiq for _, etiq in opciones]
            codigos = [cod for cod, _ in opciones]
            idx_default = codigos.index(27) if 27 in codigos else 0
            elegido = st.selectbox("Aglomerado", etiquetas, index=idx_default)
            aglomerado = codigos[etiquetas.index(elegido)]

        year_mode = st.radio("Selección de años", ["Un año", "Rango"], horizontal=True)
        if year_mode == "Un año":
            year_single = st.number_input(
                "Año",
                min_value=YEAR_MIN,
                max_value=YEAR_MAX,
                value=min(YEAR_MAX, PROYECTO_CUYO_YEAR_MAX),
                step=1,
            )
            years = [int(year_single)]
        else:
            y_min = st.number_input(
                "Desde",
                min_value=YEAR_MIN,
                max_value=YEAR_MAX,
                value=max(YEAR_MIN, PROYECTO_CUYO_YEAR_MIN),
                step=1,
            )
            y_max = st.number_input(
                "Hasta",
                min_value=YEAR_MIN,
                max_value=YEAR_MAX,
                value=min(YEAR_MAX, PROYECTO_CUYO_YEAR_MAX),
                step=1,
            )
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
        todos = st.checkbox("Todos los análisis", value=True)
        if todos:
            analisis = ["todos"]
        else:
            analisis = st.multiselect(
                "Seleccionar",
                ANALISIS_UI,
                default=["descriptivos", "correlaciones", "logistica", "cluster", "shap"],
            )

        fmt_excel = st.checkbox("Generar Excel", value=True)
        fmt_word = st.checkbox("Generar Word", value=True)
        force = st.checkbox("Forzar nueva descarga", value=False)

        ejecutar = st.button("Ejecutar análisis", type="secondary", use_container_width=True)

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
            aglomerados=solicitud.aglomerados_filtro,
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
        st.session_state["modo_proyecto_cuyo"] = False
        status.update(label="Análisis completado", state="complete")

resultado = st.session_state.get("indec_resultado")
solicitud_guardada: SolicitudAnalisis | None = st.session_state.get("indec_solicitud")
modo_proyecto = bool(st.session_state.get("modo_proyecto_cuyo"))

if resultado and solicitud_guardada:
    tablas = resultado.get("tablas", {})
    corr = resultado.get("correlacion_destacada")
    corr_txt = f"{corr:.3f}" if isinstance(corr, (float, int)) else "N/D"
    st.success(
        f"Resultados listos — {resultado['meta'].get('registros', 0):,} registros · "
        f"correlación exclusión↔movilidad: {corr_txt}"
    )

    c1, c2, c3 = st.columns(3)
    slug = "proyecto_cuyo" if modo_proyecto else solicitud_guardada.label
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
                ambito=resultado["meta"].get("ambito", solicitud_guardada.label),
            ),
            file_name=f"informe_eph_{slug}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )

    # --- Vista Proyecto Cuyo ---
    if modo_proyecto:
        st.subheader("Hallazgos por objetivo del proyecto")
        hallazgos = resultado.get("hallazgos") or []
        for h in hallazgos:
            st.markdown(f"**{h.get('objetivo', '')}**  \n{h.get('hallazgo', '')}")

        comp = tablas.get("comparativo_ambitos")
        if comp is not None and not comp.empty:
            st.subheader("Comparativo Nación / Cuyo / provincias")
            st.dataframe(comp, use_container_width=True, hide_index=True)
            y_cols = [
                c
                for c in ["idx_exclusion_digital", "score_movilidad_proxy", "vulnerabilidad_social"]
                if c in comp.columns
            ]
            if y_cols:
                fig_comp = px.bar(
                    comp,
                    x="label",
                    y=y_cols,
                    barmode="group",
                    color_discrete_sequence=CHART_COLORS,
                    labels={"value": "Índice", "label": "Ámbito", "variable": "Indicador"},
                    title="Exclusión digital, movilidad y vulnerabilidad por ámbito",
                )
                fig_comp.update_layout(template="plotly_white")
                st.plotly_chart(fig_comp, use_container_width=True)

        perf = tablas.get("perfiles_vulnerables")
        if perf is not None and not perf.empty:
            st.subheader("Perfiles vulnerables (OE3)")
            st.dataframe(perf, use_container_width=True, hide_index=True)
            cuyo_perf = perf.loc[perf["ambito"] == "gran_cuyo"] if "ambito" in perf.columns else perf
            if not cuyo_perf.empty and "idx_exclusion_digital" in cuyo_perf.columns:
                fig_p = px.bar(
                    cuyo_perf.sort_values("idx_exclusion_digital"),
                    x="idx_exclusion_digital",
                    y="perfil",
                    orientation="h",
                    color_discrete_sequence=[CHART_COLORS[2]],
                    title="Exclusión digital por perfil — Gran Cuyo",
                    labels={"idx_exclusion_digital": "Índice exclusión digital", "perfil": "Perfil"},
                )
                fig_p.update_layout(template="plotly_white")
                st.plotly_chart(fig_p, use_container_width=True)

    shap_tab = tablas.get("shap_importancia") or tablas.get("cuyo_shap_importancia")
    if shap_tab is not None and not shap_tab.empty:
        st.subheader("Importancia SHAP")
        shap_plot = shap_tab.copy()
        shap_plot["variable_legible"] = shap_plot["variable"].map(nombre_completo)
        shap_plot = shap_plot.sort_values("peso_relativo_pct")
        fig_shap = px.bar(
            shap_plot,
            x="peso_relativo_pct",
            y="variable_legible",
            orientation="h",
            color_discrete_sequence=[CHART_COLORS[0]],
            labels={
                "peso_relativo_pct": "Peso relativo (%)",
                "variable_legible": "Variable",
            },
            title="Variables que más explican la predicción",
        )
        fig_shap.update_layout(template="plotly_white", height=max(360, len(shap_plot) * 34))
        st.plotly_chart(fig_shap, use_container_width=True)

        graf_shap = resultado.get("grafico_shap")
        if graf_shap and Path(graf_shap).exists():
            c3.image(graf_shap, caption="Resumen SHAP (barras)")
        detalle = (resultado.get("modelos", {}).get("shap") or {}).get("grafico_detalle")
        if detalle and Path(detalle).exists():
            with st.expander("Detalle SHAP (distribución, outliers recortados)"):
                st.image(detalle, use_container_width=True)

    desc = tablas.get("descriptivos_anuales") or tablas.get("cuyo_descriptivos_anuales")
    if desc is not None and not desc.empty:
        guia = resumen_interpretacion_indices(desc)
        if guia:
            with st.expander("Guía de interpretación (bajo / medio / alto)", expanded=True):
                st.markdown(
                    "- Escala de referencia para índices entre 0 y 1: **Bajo < 0,33 · Medio 0,33-0,66 · Alto > 0,66**.\n"
                    "- En **exclusión** y **vulnerabilidad**, alto = peor situación.\n"
                    "- En **movilidad (proxy)**, alto = mejor situación."
                )
                st.dataframe(pd.DataFrame(guia), use_container_width=True, hide_index=True)

        st.subheader("Evolución anual")
        y_cols = [
            c
            for c in ["idx_exclusion_digital", "score_movilidad_proxy", "vulnerabilidad_social"]
            if c in desc.columns
        ]
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

    evo = resultado.get("grafico_evolucion")
    if evo and Path(evo).exists():
        st.subheader("Evolución del índice de exclusión digital")
        st.image(evo, use_container_width=True)
