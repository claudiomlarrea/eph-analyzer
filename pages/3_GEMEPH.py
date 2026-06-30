# -*- coding: utf-8 -*-
"""GEMEPH — Gemelo sociodemográfico de los 31 aglomerados urbanos de Argentina."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from gemeph.baseline import build_baseline, load_baseline
from gemeph.catalog import build_catalog, catalog_to_dataframe, load_catalog, persist_gemeph_run
from gemeph.config import APP_NAME, APP_SUBTITLE, MIN_N_ADVERTENCIA
from gemeph.panel import load_or_build_panel, periodo_texto
from gemeph.territories import list_territories, territory_label
from indec_auto.src.config import YEAR_MAX, YEAR_MIN

CHART_COLORS = ["#1f4e79", "#2e7d32", "#c62828", "#6a1b9a", "#ef6c00"]

st.set_page_config(page_title=APP_NAME, page_icon="🪞", layout="wide")

st.title(f"{APP_NAME}")
st.caption(APP_SUBTITLE)
st.markdown(
    "Descarga automática de microdatos INDEC (hogar + individuo), construye un **estado territorial** "
    "para Argentina y cada uno de los **31 aglomerados urbanos**, y permite compararlos."
)


def _territorio_options() -> tuple[list[str], dict[str, str]]:
    items = list_territories()
    labels = {t["id"]: f"{t['nombre']}" + (f" ({t['codigo']})" if t["codigo"] else "") for t in items}
    ids = [t["id"] for t in items]
    return ids, labels


@st.cache_data(show_spinner="Construyendo panel maestro INDEC…", ttl=86400)
def _cargar_gemeph(
    years: tuple[int, ...],
    trimestre: int,
    modulo: str,
    force: bool,
) -> tuple[pd.DataFrame, dict, str]:
    return load_or_build_panel(list(years), trimestre, modulo=modulo, force_download=force)


@st.cache_data(show_spinner="Calculando catálogo territorial…", ttl=3600)
def _catalogo_desde_panel(_panel_key: str, panel: pd.DataFrame, periodo: str, modulo: str) -> dict:
    return build_catalog(panel, periodo=periodo, modulo=modulo)


@st.cache_data(show_spinner=False, ttl=3600)
def _baseline_territorio(
    _panel_key: str,
    panel: pd.DataFrame,
    territory_id: str,
    periodo: str,
    modulo: str,
) -> dict:
    cached_run = st.session_state.get("gemeph_run_id")
    if cached_run:
        bl = load_baseline(cached_run, territory_id)
        if bl:
            return bl
    return build_baseline(panel, territory_id, periodo=periodo, modulo=modulo, include_clusters=True)


with st.sidebar:
    st.subheader("Configuración del gemelo")
    modulo = st.selectbox(
        "Módulo",
        options=["tic", "base"],
        format_func=lambda x: "Hogar + Individuo + TIC" if x == "tic" else "Hogar + Individuo (base)",
    )
    year_mode = st.radio("Años", ["Un año", "Rango"], horizontal=True)
    if year_mode == "Un año":
        year_single = st.number_input("Año", min_value=YEAR_MIN, max_value=YEAR_MAX, value=min(2022, YEAR_MAX), step=1)
        years = [int(year_single)]
    else:
        y_min = st.number_input("Desde", min_value=YEAR_MIN, max_value=YEAR_MAX, value=2017, step=1)
        y_max = st.number_input("Hasta", min_value=YEAR_MIN, max_value=YEAR_MAX, value=min(2024, YEAR_MAX), step=1)
        if y_min > y_max:
            y_min, y_max = y_max, y_min
        years = list(range(int(y_min), int(y_max) + 1))

    trimestre_default = 4 if modulo == "tic" else 1
    trimestre = st.selectbox("Trimestre", [1, 2, 3, 4], index=trimestre_default - 1)
    if modulo == "tic" and trimestre != 4:
        st.info("El módulo TIC suele corresponder al 4.º trimestre.")

    force = st.checkbox("Forzar nueva descarga INDEC", value=False)
    guardar_disco = st.checkbox("Guardar baselines en disco (data/gemeph/)", value=False)

    if st.button("Actualizar GEMEPH", type="primary", use_container_width=True):
        st.session_state["gemeph_force"] = True

territory_ids, territory_labels = _territorio_options()
force_run = st.session_state.pop("gemeph_force", False)

periodo = periodo_texto(years, trimestre)

try:
    panel, val, run_id = _cargar_gemeph(tuple(years), trimestre, modulo, force or force_run)
except Exception as exc:
    st.error(f"No pude descargar o preparar los microdatos INDEC.\n\nDetalle: {exc}")
    st.stop()

st.session_state["gemeph_run_id"] = run_id
panel_key = f"{run_id}_{len(panel)}"

if guardar_disco and force_run:
    persist_gemeph_run(panel, run_id=run_id, periodo=periodo, modulo=modulo, save_panel_parquet=True)
    st.sidebar.success("Baselines guardados en disco.")

catalog = _catalogo_desde_panel(panel_key, panel, periodo, modulo)
cat_df = catalog_to_dataframe(catalog)

st.success(
    f"Panel maestro: **{len(panel):,}** registros individuales · "
    f"Período **{periodo}** · **{catalog['n_territorios']}** territorios"
)

tab_estado, tab_comparar, tab_evolucion = st.tabs(["Estado del gemelo", "Comparar aglomerados", "Evolución"])

with tab_estado:
    col_sel, col_info = st.columns([2, 1])
    with col_sel:
        buscar = st.text_input("Buscar aglomerado", placeholder="Ej. San Juan, Mendoza, Rosario…")
        opciones = territory_ids
        if buscar.strip():
            q = buscar.strip().lower()
            opciones = [tid for tid in territory_ids if q in territory_labels[tid].lower()]
        if not opciones:
            opciones = territory_ids
        territorio_id = st.selectbox(
            "Territorio",
            opciones,
            format_func=lambda x: territory_labels[x],
        )
    with col_info:
        fila = cat_df.loc[cat_df["territorio_id"] == territorio_id]
        if not fila.empty:
            n = int(fila.iloc[0].get("n_individuos", 0))
            st.metric("Individuos en muestra", f"{n:,}")
            if n < MIN_N_ADVERTENCIA:
                st.warning("Muestra muy pequeña: interpretar con cautela.")

    baseline = _baseline_territorio(panel_key, panel, territorio_id, periodo, modulo)
    kpis = baseline.get("kpis", {})

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ocupación", f"{kpis.get('pct_ocupado', '—')}%")
    m2.metric("Educación superior", f"{kpis.get('pct_superior', '—')}%")
    m3.metric("Movilidad (proxy)", f"{kpis.get('score_movilidad_proxy', '—')}")
    m4.metric("Vulnerabilidad social", f"{kpis.get('vulnerabilidad_social', '—')}")

    if modulo == "tic" and kpis.get("idx_exclusion_digital") is not None:
        c1, c2, c3 = st.columns(3)
        c1.metric("Exclusión digital (índice)", f"{kpis.get('idx_exclusion_digital', '—')}")
        c2.metric("% exclusión digital alta", f"{kpis.get('pct_exclusion_digital_alta', '—')}%")
        c3.metric("Informalidad (ocupados)", f"{kpis.get('pct_informal_ocupados', '—')}%")
    else:
        st.caption("Índices digitales disponibles con módulo TIC (trimestre IV).")

    brechas = kpis.get("brechas") or {}
    if brechas:
        st.subheader("Brechas")
        bcols = st.columns(len(brechas))
        for col, (nombre, valor) in zip(bcols, brechas.items()):
            etiqueta = nombre.replace("_", " ")
            col.metric(etiqueta, f"{valor} pp")

    perfiles = baseline.get("perfiles")
    if perfiles:
        st.subheader("Perfiles sociodigitales (clústeres)")
        pdf = pd.DataFrame(perfiles)
        if "pct" in pdf.columns:
            fig_p = px.bar(
                pdf,
                x="nombre",
                y="pct",
                color_discrete_sequence=[CHART_COLORS[0]],
                labels={"nombre": "Perfil", "pct": "% de la muestra"},
                title=f"Composición de perfiles — {baseline.get('territorio_nombre')}",
            )
            fig_p.update_layout(template="plotly_white", xaxis_tickangle=-25)
            st.plotly_chart(fig_p, use_container_width=True)
        st.dataframe(pdf, use_container_width=True, hide_index=True)

with tab_comparar:
    st.subheader("Ranking de aglomerados")
    metric_opts = {
        "pct_ocupado": "Tasa de ocupación (%)",
        "pct_superior": "Educación superior (%)",
        "vulnerabilidad_social": "Vulnerabilidad social (índice)",
        "score_movilidad_proxy": "Movilidad social proxy (índice)",
    }
    if modulo == "tic":
        metric_opts["idx_exclusion_digital"] = "Exclusión digital (índice)"
        metric_opts["pct_exclusion_digital_alta"] = "Exclusión digital alta (%)"

    metrica = st.selectbox("Indicador", list(metric_opts.keys()), format_func=lambda k: metric_opts[k])
    cmp = cat_df[cat_df["tipo"] == "aglomerado"].copy()
    cmp = cmp.dropna(subset=[metrica]).sort_values(metrica, ascending=False)

    fig_rank = px.bar(
        cmp,
        x="territorio_nombre",
        y=metrica,
        color_discrete_sequence=[CHART_COLORS[1]],
        labels={"territorio_nombre": "Aglomerado", metrica: metric_opts[metrica]},
        title=f"Comparación entre aglomerados — {metric_opts[metrica]}",
    )
    fig_rank.update_layout(template="plotly_white", xaxis_tickangle=-45, height=520)
    st.plotly_chart(fig_rank, use_container_width=True)

    nacional = cat_df.loc[cat_df["territorio_id"] == "nacional"]
    if not nacional.empty and metrica in nacional.columns:
        st.caption(f"Referencia nacional: **{nacional.iloc[0][metrica]}**")

    st.dataframe(
        cmp[
            ["territorio_nombre", "aglomerado_codigo", "n_individuos", metrica]
            + ([m for m in ("idx_exclusion_digital", "pct_ocupado") if m in cmp.columns and m != metrica])
        ],
        use_container_width=True,
        hide_index=True,
    )

with tab_evolucion:
    territorio_evo = st.selectbox(
        "Territorio para evolución",
        territory_ids,
        format_func=lambda x: territory_labels[x],
        key="evo_territorio",
    )
    bl_evo = _baseline_territorio(panel_key, panel, territorio_evo, periodo, modulo)
    evo = pd.DataFrame(bl_evo.get("evolucion", []))
    if evo.empty:
        st.info("No hay serie temporal para el período seleccionado.")
    else:
        y_cols = [c for c in ("idx_exclusion_digital", "score_movilidad_proxy", "vulnerabilidad_social") if c in evo.columns]
        if y_cols:
            fig_evo = px.line(
                evo,
                x="anio",
                y=y_cols,
                markers=True,
                color_discrete_sequence=CHART_COLORS,
                labels={"value": "Índice", "anio": "Año"},
                title=f"Evolución — {territory_label(territorio_evo)}",
            )
            fig_evo.update_layout(template="plotly_white", legend_title_text="Indicador")
            st.plotly_chart(fig_evo, use_container_width=True)
        st.dataframe(evo, use_container_width=True, hide_index=True)

st.caption("Fuente: INDEC — EPH continua (microdatos hogar e individuo). GEMEPH no es proyección oficial INDEC.")
