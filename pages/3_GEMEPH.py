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
from gemeph.mapviz import build_map_figure, metric_choices
from gemeph.panel import load_or_build_panel, periodo_texto
from gemeph.export import (
    export_baseline_excel_bytes,
    export_catalog_excel_bytes,
    export_catalog_json_bytes,
    export_scenario_excel_bytes,
    export_scenario_json_bytes,
    export_word_bytes,
)
from gemeph.scenario import compare_rows, lever_baselines, run_scenario
from gemeph.territories import filter_territory, list_territories, territory_label
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

export_meta = {
    "titulo": APP_NAME,
    "periodo": periodo,
    "modulo": modulo,
    "fuente": "INDEC — EPH (hogar + individuo)",
    "registros_panel": len(panel),
    "n_territorios": int(catalog.get("n_territorios", 0)),
}

with st.sidebar:
    st.divider()
    st.subheader("Exportar")
    slug = run_id.replace(" ", "_")
    exp_territorio = st.selectbox(
        "Territorio para informe / baseline",
        territory_ids,
        format_func=lambda x: territory_labels[x],
        key="exp_territorio",
    )
    bl_export = _baseline_territorio(panel_key, panel, exp_territorio, periodo, modulo)

    st.download_button(
        "Catálogo Excel (31 aglom.)",
        data=export_catalog_excel_bytes(cat_df, export_meta),
        file_name=f"gemeph_catalogo_{slug}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    st.download_button(
        "Catálogo JSON",
        data=export_catalog_json_bytes(catalog),
        file_name=f"gemeph_catalogo_{slug}.json",
        mime="application/json",
        use_container_width=True,
    )
    st.download_button(
        "Baseline Excel (territorio)",
        data=export_baseline_excel_bytes(bl_export, export_meta),
        file_name=f"gemeph_baseline_{exp_territorio}_{slug}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    st.download_button(
        "Informe Word ejecutivo",
        data=export_word_bytes(
            titulo=f"{APP_NAME} — {territory_label(exp_territorio)}",
            periodo=periodo,
            cat_df=cat_df,
            baseline=bl_export,
            scenario=st.session_state.get("gemeph_last_scenario"),
        ),
        file_name=f"gemeph_informe_{slug}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True,
    )
    last_scn = st.session_state.get("gemeph_last_scenario")
    if last_scn:
        scn_meta = {
            **export_meta,
            "territorio": st.session_state.get("gemeph_last_scenario_territorio", ""),
        }
        st.download_button(
            "Escenario Excel",
            data=export_scenario_excel_bytes(last_scn, scn_meta),
            file_name=f"gemeph_escenario_{slug}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        st.download_button(
            "Escenario JSON",
            data=export_scenario_json_bytes(last_scn, scn_meta),
            file_name=f"gemeph_escenario_{slug}.json",
            mime="application/json",
            use_container_width=True,
        )

st.success(
    f"Panel maestro: **{len(panel):,}** registros individuales · "
    f"Período **{periodo}** · **{catalog['n_territorios']}** territorios"
)

tab_estado, tab_mapa, tab_comparar, tab_evolucion, tab_escenarios = st.tabs(
    ["Estado del gemelo", "Mapa territorial", "Comparar aglomerados", "Evolución", "Escenarios (what-if)"]
)

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
        estado_default = st.session_state.get("gemeph_estado_territorio")
        estado_index = opciones.index(estado_default) if estado_default in opciones else 0
        territorio_id = st.selectbox(
            "Territorio",
            opciones,
            index=estado_index,
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

with tab_mapa:
    st.subheader("Mapa de aglomerados urbanos")
    st.caption("Tamaño del punto ≈ muestra · color = indicador seleccionado · clic en la leyenda para filtrar.")

    map_metrics = metric_choices(modulo == "tic")
    map_metric = st.selectbox(
        "Indicador en el mapa",
        list(map_metrics.keys()),
        format_func=lambda k: map_metrics[k],
        key="map_metric",
    )

    aglo_opts = cat_df.loc[cat_df["tipo"] == "aglomerado", ["aglomerado_codigo", "territorio_nombre"]].dropna()
    aglo_codes = [int(c) for c in aglo_opts["aglomerado_codigo"]]
    aglo_labels = dict(zip(aglo_opts["aglomerado_codigo"].astype(int), aglo_opts["territorio_nombre"]))

    default_idx = aglo_codes.index(27) if 27 in aglo_codes else 0
    highlight = st.selectbox(
        "Destacar aglomerado",
        aglo_codes,
        index=default_idx,
        format_func=lambda c: aglo_labels.get(c, str(c)),
        key="map_highlight",
    )

    fig_map = build_map_figure(
        cat_df,
        map_metric,
        highlight_codigo=highlight,
        metric_label=map_metrics[map_metric],
    )
    st.plotly_chart(fig_map, use_container_width=True)

    hi_row = cat_df.loc[cat_df["aglomerado_codigo"] == highlight]
    if not hi_row.empty:
        r = hi_row.iloc[0]
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Aglomerado", r["territorio_nombre"])
        mc2.metric(map_metrics[map_metric], f"{r.get(map_metric, '—')}")
        mc3.metric("Ocupación", f"{r.get('pct_ocupado', '—')}%")
        if modulo == "tic":
            mc4.metric("Exclusión digital", f"{r.get('idx_exclusion_digital', '—')}")

    if st.button("Abrir estado detallado de este aglomerado", key="map_to_estado"):
        st.session_state["gemeph_estado_territorio"] = f"aglomerado_{highlight}"
        st.toast(f"Elegí la pestaña «Estado del gemelo» — {aglo_labels.get(highlight, '')}")

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

with tab_escenarios:
    st.subheader("Simulación predictiva (escenarios contrafactuales)")
    st.markdown(
        "Ajustá las barras para simular **qué pasaría** si mejoran conectividad, educación o empleo formal. "
        "Los indicadores se recalculan sobre los microdatos del territorio; el modelo logístico estima "
        "la probabilidad agregada de exclusión digital alta."
    )

    if modulo != "tic":
        st.warning(
            "Para escenarios de **exclusión digital** activá el módulo **Hogar + Individuo + TIC** "
            "y el **trimestre IV** en la barra lateral. Podés igualmente simular educación y empleo formal."
        )

    territorio_scn = st.selectbox(
        "Territorio del escenario",
        territory_ids,
        format_func=lambda x: territory_labels[x],
        key="scn_territorio",
    )
    df_territorio = filter_territory(panel, territorio_scn)
    include_tic = modulo == "tic"
    bases = lever_baselines(df_territorio, include_tic=include_tic)

    if df_territorio.empty:
        st.error("Sin datos para este territorio en el período seleccionado.")
    else:
        st.caption(
            f"**{territory_label(territorio_scn)}** · {len(df_territorio):,} individuos en muestra · "
            "valores iniciales = situación actual (baseline)"
        )

        targets: dict[str, float] = {}

        c1, c2 = st.columns(2)
        with c1:
            if include_tic and "internet_quintil_i" in bases:
                targets["internet_quintil_i"] = st.slider(
                    "Internet en hogares del quintil I (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(bases["internet_quintil_i"]),
                    step=1.0,
                    help="Porcentaje de personas de bajos ingresos cuyo hogar tiene internet.",
                )
            targets["pct_superior"] = st.slider(
                "Educación universitaria completa (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(bases.get("pct_superior", 0.0)),
                step=1.0,
            )
        with c2:
            targets["pct_empleo_formal"] = st.slider(
                "Empleo formal entre ocupados (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(bases.get("pct_empleo_formal", 0.0)),
                step=1.0,
                help="Ocupados con descuentos jubilatorios (proxy de formalidad).",
            )

        hay_cambio = any(
            abs(targets.get(k, 0) - bases.get(k, 0)) > 0.5
            for k in targets
        )

        if st.button("Simular escenario", type="primary", use_container_width=True) or hay_cambio:
            resultado_scn = run_scenario(df_territorio, targets, include_tic=include_tic)
            st.session_state["gemeph_last_scenario"] = resultado_scn
            st.session_state["gemeph_last_scenario_territorio"] = territory_label(territorio_scn)
            cmp_df = compare_rows(resultado_scn)

            if cmp_df.empty:
                st.info("No hay indicadores comparables para este territorio.")
            else:
                st.markdown("#### Baseline vs escenario")
                cmp_show = cmp_df.copy()
                for col in ("Baseline", "Escenario", "Cambio"):
                    cmp_show[col] = cmp_show[col].apply(
                        lambda x: f"{x:+.4g}" if col == "Cambio" and pd.notna(x) else (f"{x:.4g}" if pd.notna(x) else "—")
                    )
                st.dataframe(cmp_show, use_container_width=True, hide_index=True)

                plot_df = cmp_df.dropna(subset=["Baseline", "Escenario"]).copy()
                if not plot_df.empty:
                    plot_long = plot_df.melt(
                        id_vars=["Indicador"],
                        value_vars=["Baseline", "Escenario"],
                        var_name="Situación",
                        value_name="Valor",
                    )
                    fig_scn = px.bar(
                        plot_long,
                        x="Indicador",
                        y="Valor",
                        color="Situación",
                        barmode="group",
                        color_discrete_sequence=[CHART_COLORS[0], CHART_COLORS[2]],
                        title=f"Comparación — {territory_label(territorio_scn)}",
                    )
                    fig_scn.update_layout(template="plotly_white", xaxis_tickangle=-25, height=420)
                    st.plotly_chart(fig_scn, use_container_width=True)

            modelo = resultado_scn.get("modelo", {})
            if include_tic and modelo.get("pct_exclusion_predicho_base") is not None:
                st.markdown("#### Modelo predictivo (logística)")
                m1, m2, m3 = st.columns(3)
                m1.metric("Prob. exclusión alta (baseline)", f"{modelo['pct_exclusion_predicho_base']}%")
                m2.metric(
                    "Prob. exclusión alta (escenario)",
                    f"{modelo.get('pct_exclusion_predicho_escenario', '—')}%",
                )
                if modelo.get("pct_exclusion_predicho_escenario") is not None:
                    delta_p = round(
                        modelo["pct_exclusion_predicho_escenario"] - modelo["pct_exclusion_predicho_base"],
                        2,
                    )
                    m3.metric("Cambio estimado", f"{delta_p:+.2f} pp")
            elif modelo.get("nota"):
                st.caption(modelo["nota"])

            st.info(
                "**Interpretación:** escenario contrafactual analítico, no proyección oficial INDEC. "
                "Útil para comparar políticas; no implica causalidad estricta."
            )

st.caption("Fuente: INDEC — EPH continua (microdatos hogar e individuo). GEMEPH no es proyección oficial INDEC.")
