"""
eph-analyzer — App Streamlit.

Punto de entrada. Permite al usuario:
    1. Cargar cualquier base EPH del INDEC (xlsx, csv, txt, zip).
    2. Detectar automáticamente el tipo (hogar / individuo / TIC).
    3. Ejecutar análisis estadísticos descriptivos e inferenciales.
    4. Calcular el índice de exclusión digital.
    5. Entrenar modelos predictivos (logística, árbol, Random Forest).
    6. Interpretar resultados con SHAP.
    7. Identificar clústeres / segmentos vulnerables.
    8. Descargar resultados en Excel.

Ejecutar:
    streamlit run app.py
"""

from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

warnings.filterwarnings("ignore")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from src.analisis.correlaciones import (
    correlaciones_con_p,
    cronbach_alpha,
    matriz_correlacion,
)
from src.analisis.descriptivo import (
    estadisticos,
    frecuencias,
    tabla_cruzada,
)
from src.analisis.desigualdad import (
    comparar_por_grupo,
    gini,
    quintiles,
    razon_quintil,
    theil,
)
from src.data_cleaner import DataCleaner
from src.data_loader import cargar_eph
from src.etiquetador import (
    nombre_completo,
    nombre_variable,
    renombrar_columna_de_variables,
    renombrar_dataframe,
)
from src.file_detector import FileDetector
from src.indice_exclusion import calcular_indice_exclusion
from src.merger import mergear
from src.modelos._prep import construir_target_binario
from src.modelos.arbol_decision import correr_arbol
from src.modelos.clusters import jerarquico_cluster, kmeans_cluster
from src.modelos.logistica import correr_logistica
from src.modelos.random_forest import correr_random_forest
from src.modelos.shap_xai import (
    dependence_plot_objeto,
    explicar_modelo,
    importance_bar_objeto,
    summary_plot_objeto,
)

UPLOAD_DIR = ROOT / "data" / "usuario"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(
    page_title="eph-analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# UTILIDADES DE SESIÓN
# =============================================================================

def init_state() -> None:
    """Inicializa keys de session_state con defaults."""
    defaults = {
        "df_individuo": None,
        "df_hogar": None,
        "df_trabajado": None,
        "deteccion_individuo": None,
        "deteccion_hogar": None,
        "modo": "Guiado",
        "indice_calculado": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


@st.cache_data(show_spinner=False)
def _cargar_archivo_subido(archivo_bytes: bytes, nombre: str) -> pd.DataFrame:
    """Cachea la carga de un archivo subido por bytes."""
    destino = UPLOAD_DIR / nombre
    destino.write_bytes(archivo_bytes)
    df = cargar_eph(destino)
    return df


@st.cache_resource(show_spinner=False)
def _detector():
    return FileDetector()


@st.cache_resource(show_spinner=False)
def _cleaner():
    return DataCleaner()


def _df_a_excel_bytes(df: pd.DataFrame, nombre_hoja: str = "datos") -> bytes:
    """Convierte un DataFrame a bytes XLSX para st.download_button."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name=nombre_hoja[:31], index=False)
    return buf.getvalue()


def _boton_descargar(df: pd.DataFrame, nombre: str, label: str = "Descargar Excel") -> None:
    if df is None or len(df) == 0:
        return
    st.download_button(
        label=f"⬇ {label}",
        data=_df_a_excel_bytes(df, nombre),
        file_name=f"{nombre}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"dl_{nombre}",
    )


# =============================================================================
# SIDEBAR — CARGA DE ARCHIVOS Y CONFIGURACIÓN
# =============================================================================

def sidebar_carga() -> None:
    st.sidebar.title("📊 eph-analyzer")
    st.sidebar.caption(
        "Análisis de microdatos EPH del INDEC: descriptivo, inferencial, "
        "predictivo y XAI."
    )
    st.sidebar.divider()

    st.sidebar.header("1️⃣ Cargar bases")

    archivo_indiv = st.sidebar.file_uploader(
        "Base de individuos (obligatoria)",
        type=["xlsx", "xls", "csv", "txt", "zip", "parquet"],
        key="up_indiv",
        help="Archivo con una fila por persona (CODUSU + NRO_HOGAR + COMPONENTE).",
    )
    archivo_hogar = st.sidebar.file_uploader(
        "Base de hogares (opcional)",
        type=["xlsx", "xls", "csv", "txt", "zip", "parquet"],
        key="up_hog",
        help=(
            "Si la base de individuos ya trae las variables de hogar (lo habitual "
            "en la EPH del INDEC), no es necesaria."
        ),
    )

    if st.sidebar.button("🔄 Procesar archivos", type="primary", use_container_width=True):
        if archivo_indiv is None:
            st.sidebar.error("Subí al menos la base de individuos.")
            return

        with st.spinner("Cargando individuos..."):
            df_i = _cargar_archivo_subido(archivo_indiv.getvalue(), archivo_indiv.name)
            det_i = _detector().detectar(df_i.columns)
            st.session_state["df_individuo"] = df_i
            st.session_state["deteccion_individuo"] = det_i

        df_h = None
        det_h = None
        if archivo_hogar is not None:
            with st.spinner("Cargando hogares..."):
                df_h = _cargar_archivo_subido(archivo_hogar.getvalue(), archivo_hogar.name)
                det_h = _detector().detectar(df_h.columns)
                st.session_state["df_hogar"] = df_h
                st.session_state["deteccion_hogar"] = det_h

        with st.spinner("Mergeando + limpiando..."):
            res_merge = mergear(df_h, df_i)
            df_clean = _cleaner().limpiar(res_merge.df)
            st.session_state["df_trabajado"] = df_clean
            st.session_state["indice_calculado"] = False

        st.sidebar.success(f"✓ Listo. {df_clean.shape[0]:,} filas × {df_clean.shape[1]:,} columnas.")

    st.sidebar.divider()

    if st.session_state.get("df_trabajado") is not None:
        st.sidebar.header("2️⃣ Modo")
        st.session_state["modo"] = st.sidebar.radio(
            "Modo de uso",
            ["Guiado", "Experto"],
            help=(
                "**Guiado**: la app calcula la variable de exclusión digital y "
                "elige predictoras automáticamente. **Experto**: vos elegís todo."
            ),
            label_visibility="collapsed",
        )

    st.sidebar.divider()
    with st.sidebar.expander("ℹ Acerca de"):
        st.markdown(
            """
            Versión **0.1.0** · MIT
            Basado en la metodología de:
            *Larrea, C. (2025). Inclusión digital y movilidad social en la
            Argentina postpandemia. UNQ.*
            """
        )


# =============================================================================
# SECCIÓN: VISTA GENERAL
# =============================================================================

def seccion_overview() -> None:
    df = st.session_state["df_trabajado"]
    det_i = st.session_state["deteccion_individuo"]
    det_h = st.session_state["deteccion_hogar"]

    st.header("Vista general")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Filas", f"{df.shape[0]:,}")
    col2.metric("Columnas", f"{df.shape[1]:,}")
    col3.metric(
        "Año (si está)",
        f"{int(df['ANO4'].iloc[0])}" if "ANO4" in df.columns and len(df) > 0 else "n/d",
    )
    col4.metric(
        "Trimestre",
        f"{int(df['TRIMESTRE'].iloc[0])}" if "TRIMESTRE" in df.columns and len(df) > 0 else "n/d",
    )

    st.subheader("Detección automática")
    cols = st.columns(2 if det_h else 1)
    cols[0].info(f"**Individuos**: {det_i}")
    if det_h:
        cols[1].info(f"**Hogares**: {det_h}")

    with st.expander("📋 Primeras 10 filas"):
        st.dataframe(df.head(10), use_container_width=True)

    with st.expander("📋 Listado de columnas y tipos"):
        info_cols = pd.DataFrame({
            "columna": df.columns,
            "nombre_legible": [nombre_variable(c) for c in df.columns],
            "tipo": [str(t) for t in df.dtypes],
            "n_nulos": df.isna().sum().values,
            "%_nulos": (df.isna().sum() / len(df) * 100).round(2).values,
            "n_unicos": [df[c].nunique(dropna=True) for c in df.columns],
        })
        st.dataframe(info_cols, use_container_width=True, height=400)
        _boton_descargar(info_cols, "info_columnas", "Descargar info de columnas")


# =============================================================================
# SECCIÓN: DESCRIPTIVO
# =============================================================================

def seccion_descriptivo() -> None:
    df = st.session_state["df_trabajado"]

    st.header("📈 Estadística descriptiva")

    tab_freq, tab_estad, tab_cross = st.tabs([
        "Frecuencias", "Estadísticos numéricos", "Tabla cruzada",
    ])

    with tab_freq:
        st.markdown("Tabla de frecuencias (ponderada por `PONDERA` cuando está disponible).")
        cat_cols = [
            c for c in df.columns
            if df[c].dtype.name in ("category", "string", "object")
            or df[c].nunique(dropna=True) <= 30
        ]
        col_freq = st.selectbox(
            "Variable", options=cat_cols, key="freq_var",
            format_func=nombre_completo,
        )
        if col_freq:
            tabla = frecuencias(df, col_freq)
            st.dataframe(tabla, use_container_width=True)
            _boton_descargar(tabla, f"frecuencias_{col_freq}")

    with tab_estad:
        st.markdown("Resumen estadístico de variables numéricas (ponderado).")
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        col_num = st.selectbox(
            "Variable numérica", options=num_cols, key="estad_var",
            format_func=nombre_completo,
        )
        if col_num:
            res = estadisticos(df, col_num)
            st.dataframe(
                res.to_frame().T,
                use_container_width=True,
                hide_index=True,
            )

    with tab_cross:
        st.markdown("Cruzamiento entre dos variables (% por fila).")
        col_f, col_c = st.columns(2)
        cat_cols_cross = [
            c for c in df.columns
            if df[c].nunique(dropna=True) <= 20
        ]
        var_fila = col_f.selectbox(
            "Variable fila", options=cat_cols_cross, key="cross_fila",
            format_func=nombre_completo,
        )
        var_col = col_c.selectbox(
            "Variable columna", options=cat_cols_cross, key="cross_col",
            format_func=nombre_completo,
        )
        if var_fila and var_col and var_fila != var_col:
            cross = tabla_cruzada(df, var_fila, var_col, normalizar="fila")
            st.dataframe(cross, use_container_width=True)
            _boton_descargar(cross.reset_index(), f"crosstab_{var_fila}_{var_col}")


# =============================================================================
# SECCIÓN: DESIGUALDAD
# =============================================================================

def seccion_desigualdad() -> None:
    df = st.session_state["df_trabajado"]

    st.header("📉 Desigualdad de ingresos")

    candidatos_ingreso = [c for c in ["IPCF", "ITF", "P21", "P47T"] if c in df.columns]
    if not candidatos_ingreso:
        st.warning("La base no tiene columnas de ingreso (IPCF/ITF/P21/P47T).")
        return

    col_left, col_right = st.columns([2, 1])
    var_ing = col_left.selectbox(
        "Variable de ingreso", candidatos_ingreso, key="des_var",
        format_func=nombre_completo,
    )
    n_grupos = col_right.radio("Grupos", [5, 10], horizontal=True, key="des_n",
                               help="5 = quintiles, 10 = deciles")

    pond = "PONDIH" if "PONDIH" in df.columns else "PONDII" if "PONDII" in df.columns else None

    q = quintiles(df, var_ing, ponderador=pond, n_grupos=n_grupos)
    st.subheader(f"{'Quintiles' if n_grupos == 5 else 'Deciles'} ponderados")
    st.dataframe(q, use_container_width=True, hide_index=True)
    _boton_descargar(q, f"{'quintiles' if n_grupos==5 else 'deciles'}_{var_ing}")

    st.subheader("Indicadores de desigualdad")
    g = gini(df, var_ing, ponderador=pond)
    t = theil(df, var_ing, ponderador=pond)
    razon = razon_quintil(df, var_ing, ponderador=pond)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gini", g)
    c2.metric("Theil T", t["theil_T"])
    c3.metric("Theil L", t["theil_L"])
    c4.metric("Razón Q5/Q1", razon)

    with st.expander("ℹ Cómo se interpretan"):
        st.markdown("""
        - **Gini**: entre 0 (igualdad perfecta) y 1 (concentración total).
          En Argentina suele oscilar 0.40–0.45.
        - **Theil**: T pesa más la cima, L pesa más la base.
        - **Razón Q5/Q1**: cuántas veces el ingreso medio del 20% más rico
          supera al del 20% más pobre.
        """)

    if "REGION" in df.columns:
        st.subheader("Comparación regional")
        comp = comparar_por_grupo(df, var_ing, "REGION", ponderador=pond)
        st.dataframe(comp, use_container_width=True, hide_index=True)
        _boton_descargar(comp, f"region_{var_ing}")


# =============================================================================
# SECCIÓN: CORRELACIONES
# =============================================================================

def seccion_correlaciones() -> None:
    df = st.session_state["df_trabajado"]

    st.header("🔗 Correlaciones y consistencia interna")

    tab_corr, tab_cron = st.tabs(["Matriz de correlación", "Alfa de Cronbach"])

    with tab_corr:
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cols_def = [
            c for c in ["CH06", "NIVEL_ED", "P21", "IPCF", "ITF", "IX_TOT", "INDICE_EXCLUSION"]
            if c in num_cols
        ]
        sel = st.multiselect(
            "Variables a correlacionar",
            options=num_cols,
            default=cols_def[:6] if cols_def else num_cols[:5],
            key="corr_sel",
            format_func=nombre_completo,
        )
        metodo = st.radio(
            "Método",
            ["pearson", "kendall", "spearman"],
            horizontal=True,
            key="corr_metodo",
        )
        if len(sel) >= 2:
            mat = matriz_correlacion(df, sel, metodo=metodo)
            mat_legible = renombrar_dataframe(mat, columnas=True, indice=True)
            st.dataframe(
                mat_legible.style.background_gradient(cmap="RdBu_r", vmin=-1, vmax=1),
                use_container_width=True,
            )

            with st.expander("Pares con valor p (top correlaciones)"):
                cp = correlaciones_con_p(df, sel, metodo=metodo)
                cp_legible = cp.copy()
                cp_legible["var_1"] = cp_legible["var_1"].map(nombre_variable)
                cp_legible["var_2"] = cp_legible["var_2"].map(nombre_variable)
                st.dataframe(cp_legible.head(20), use_container_width=True, hide_index=True)
                _boton_descargar(cp_legible, f"correlaciones_{metodo}")

    with tab_cron:
        st.markdown(
            "Alfa de Cronbach mide consistencia interna de una escala "
            "(varios ítems midiendo lo mismo)."
        )
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        candidatos = [c for c in num_cols if df[c].nunique(dropna=True) <= 20]
        items = st.multiselect(
            "Ítems de la escala",
            options=candidatos,
            key="cron_items",
            format_func=nombre_completo,
        )
        if len(items) >= 2:
            try:
                diag = cronbach_alpha(df, items)
                if isinstance(diag, dict):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Alpha", diag["alpha"])
                    c2.metric("k (ítems)", diag["k"])
                    c3.metric("n", f"{diag['n']:,}")
                    st.info(f"Interpretación: **{diag['interpretacion']}**")
                    if diag["alpha_si_quito_item"]:
                        st.markdown("**Alpha si quito el ítem**:")
                        st.dataframe(
                            pd.DataFrame.from_dict(
                                diag["alpha_si_quito_item"],
                                orient="index",
                                columns=["alpha_sin_item"],
                            )
                        )
            except Exception as e:
                st.error(f"Error: {e}")


# =============================================================================
# SECCIÓN: ÍNDICE DE EXCLUSIÓN DIGITAL
# =============================================================================

def seccion_indice() -> None:
    df = st.session_state["df_trabajado"]

    st.header("🌐 Índice compuesto de exclusión digital")
    st.markdown("""
    Construido según Larrea (2025) con tres dimensiones:
    **acceso material**, **competencias digitales** y **uso significativo**.
    Resultado en [0, 1]: 0 = inclusión, 1 = exclusión total.
    """)

    if st.button("Calcular índice", type="primary"):
        with st.spinner("Calculando..."):
            res = calcular_indice_exclusion(df)
            st.session_state["df_trabajado"] = res.df
            st.session_state["indice_calculado"] = True
            st.session_state["res_indice"] = res

    if st.session_state.get("indice_calculado"):
        res = st.session_state["res_indice"]
        df = st.session_state["df_trabajado"]

        c = res.cobertura
        col1, col2, col3 = st.columns(3)
        col1.metric("Cobertura ACCESO", f"{c['acceso_pct']:.0f}%")
        col2.metric("Cobertura COMPETENCIAS", f"{c['competencias_pct']:.0f}%")
        col3.metric("Cobertura USO", f"{c['uso_pct']:.0f}%")

        if res.advertencias:
            for a in res.advertencias:
                st.warning(a)

        st.subheader("Distribución del nivel de exclusión")
        if "NIVEL_EXCLUSION" in df.columns:
            dist = (
                df["NIVEL_EXCLUSION"]
                .value_counts(dropna=False)
                .sort_index()
                .rename_axis("nivel")
                .reset_index(name="n")
            )
            dist["%"] = (dist["n"] / dist["n"].sum() * 100).round(2)
            st.dataframe(dist, use_container_width=True, hide_index=True)
            st.bar_chart(dist.set_index("nivel")["n"])

        st.subheader("Estadísticos del índice")
        st.dataframe(
            estadisticos(df, "INDICE_EXCLUSION").to_frame().T,
            use_container_width=True,
            hide_index=True,
        )

        if "QUINTIL_IPCF" in df.columns:
            st.subheader("Promedio del índice por quintil de IPCF")
            tabla = (
                df.groupby("QUINTIL_IPCF", observed=False)["INDICE_EXCLUSION"]
                .agg(["mean", "count"])
                .round(3)
                .reset_index()
            )
            st.dataframe(tabla, use_container_width=True, hide_index=True)


# =============================================================================
# SECCIÓN: MODELOS PREDICTIVOS
# =============================================================================

def _seleccionar_target_y_features(df: pd.DataFrame) -> tuple[pd.Series | None, list[str], str]:
    """Devuelve (y, features, label_target). Maneja modo guiado / experto."""
    modo = st.session_state["modo"]

    if modo == "Guiado" and "INDICE_EXCLUSION" in df.columns:
        st.success("**Modo guiado**: target = exclusión digital binarizada (≥0.5).")
        y = construir_target_binario(df, "INDICE_EXCLUSION", umbral=0.5)
        features_def = [
            c for c in ["CH06", "CH04", "NIVEL_ED", "REGION", "IPCF", "IX_TOT", "ITF"]
            if c in df.columns
        ]
        features = st.multiselect(
            "Predictoras (modo guiado)",
            options=df.columns.tolist(),
            default=features_def,
            key="mod_feat_g",
            format_func=nombre_completo,
        )
        return y, features, "INDICE_EXCLUSION ≥ 0.5"

    if modo == "Guiado":
        st.warning("Calculá primero el índice de exclusión digital. Cambiá a modo Experto para elegir otra variable.")
        return None, [], ""

    st.info("**Modo experto**: vos elegís target y predictoras.")
    target_col = st.selectbox(
        "Variable dependiente (target)",
        options=df.columns.tolist(),
        key="mod_target",
        format_func=nombre_completo,
    )
    n_unique = df[target_col].nunique(dropna=True)
    es_binaria = n_unique == 2
    umbral = None
    valores_pos: list | None = None

    if not es_binaria:
        es_num = pd.api.types.is_numeric_dtype(df[target_col])
        if es_num:
            umbral = st.number_input(
                "Umbral para binarizar (≥ umbral → 1)",
                value=float(df[target_col].median()),
                key="mod_umbral",
            )
        else:
            valores = df[target_col].dropna().unique().tolist()[:50]
            valores_pos = st.multiselect(
                "Valores que cuentan como '1'",
                options=valores,
                key="mod_valpos",
            )
    try:
        y = construir_target_binario(
            df, target_col,
            umbral=umbral,
            valores_positivos=valores_pos,
        )
    except Exception as e:
        st.error(f"Error construyendo target: {e}")
        return None, [], ""

    features = st.multiselect(
        "Predictoras",
        options=[c for c in df.columns if c != target_col],
        default=[c for c in ["CH06", "CH04", "NIVEL_ED", "REGION", "IPCF", "IX_TOT"] if c in df.columns and c != target_col],
        key="mod_feat_e",
        format_func=nombre_completo,
    )
    return y, features, target_col


def seccion_modelos() -> None:
    df = st.session_state["df_trabajado"]

    st.header("🤖 Modelos predictivos e inferenciales")

    y, features, label_target = _seleccionar_target_y_features(df)

    if y is None or not features:
        return

    st.markdown(f"Target: `{label_target}` · {features and len(features)} predictoras")
    balance = y.value_counts(normalize=True).round(3).to_dict()
    st.caption(f"Balance: {balance}")

    tab_log, tab_arb, tab_rf = st.tabs([
        "Regresión logística", "Árbol de decisión", "Random Forest",
    ])

    with tab_log:
        if st.button("Entrenar logística", key="btn_log"):
            with st.spinner("Entrenando..."):
                res = correr_logistica(df, y, features)
                st.session_state["res_logistica"] = res
        if "res_logistica" in st.session_state:
            res = st.session_state["res_logistica"]
            _mostrar_resultado_logistica(res)

    with tab_arb:
        c1, c2 = st.columns(2)
        max_d = c1.slider("Profundidad máxima", 2, 10, 4, key="arb_d")
        min_l = c2.slider("Min hojas por nodo", 10, 1000, 200, key="arb_l")
        if st.button("Entrenar árbol", key="btn_arb"):
            with st.spinner("Entrenando..."):
                res = correr_arbol(df, y, features, max_depth=max_d, min_samples_leaf=min_l)
                st.session_state["res_arbol"] = res
        if "res_arbol" in st.session_state:
            res = st.session_state["res_arbol"]
            _mostrar_resultado_arbol(res)

    with tab_rf:
        c1, c2 = st.columns(2)
        n_est = c1.slider("Cantidad de árboles", 100, 1000, 500, step=100, key="rf_n")
        max_d_rf = c2.selectbox("Profundidad", ["Sin límite", 5, 10, 15, 20], key="rf_d")
        if st.button("Entrenar Random Forest", key="btn_rf"):
            with st.spinner(f"Entrenando ({n_est} árboles)..."):
                md = None if max_d_rf == "Sin límite" else int(max_d_rf)
                res = correr_random_forest(df, y, features, n_estimators=n_est, max_depth=md)
                st.session_state["res_rf"] = res
        if "res_rf" in st.session_state:
            res = st.session_state["res_rf"]
            _mostrar_resultado_rf(res)


def _mostrar_resultado_logistica(res) -> None:
    m = res.metricas
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Accuracy", m["accuracy_test"])
    c2.metric("AUC-ROC", m.get("auc_roc_test"))
    c3.metric("Pseudo-R²", m.get("pseudo_r2_mcfadden"))
    c4.metric("n test", f"{m['n_test']:,}")

    st.subheader("Coeficientes y odds ratios")
    cols = ["variable", "coef", "OR", "IC95_inf_OR", "IC95_sup_OR", "p_valor", "significativa_05"]
    cols = [c for c in cols if c in res.coeficientes.columns]
    coef_legible = renombrar_columna_de_variables(
        res.coeficientes[cols], "variable", incluir_codigo=True,
    )
    st.dataframe(coef_legible, use_container_width=True, hide_index=True)
    _boton_descargar(coef_legible, "coeficientes_logistica")

    with st.expander("Matriz de confusión"):
        st.dataframe(res.matriz_confusion, use_container_width=True)
    with st.expander("Curva ROC"):
        if res.roc and res.roc.get("fpr"):
            fig, ax = plt.subplots(figsize=(6, 5))
            ax.plot(res.roc["fpr"], res.roc["tpr"], color="#1f4e79", lw=2,
                    label=f"AUC = {m.get('auc_roc_test', '?')}")
            ax.plot([0, 1], [0, 1], "k--", alpha=0.4)
            ax.set_xlabel("FPR")
            ax.set_ylabel("TPR")
            ax.legend()
            st.pyplot(fig)


def _mostrar_resultado_arbol(res) -> None:
    m = res.metricas
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Accuracy", m["accuracy_test"])
    c2.metric("AUC-ROC", m.get("auc_roc_test"))
    c3.metric("Hojas", m["n_hojas"])
    c4.metric("Profundidad", m["profundidad_real"])

    st.subheader("Importancias")
    imp_legible = renombrar_columna_de_variables(
        res.importancias, "variable", incluir_codigo=True,
    )
    st.dataframe(imp_legible.head(15), use_container_width=True, hide_index=True)
    _boton_descargar(imp_legible, "importancias_arbol")

    with st.expander("Reglas del árbol (texto)"):
        st.code(res.arbol_texto, language=None)


def _mostrar_resultado_rf(res) -> None:
    m = res.metricas
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Accuracy", m["accuracy_test"])
    c2.metric("AUC-ROC", m.get("auc_roc_test"))
    c3.metric("OOB", m.get("oob_score"))
    c4.metric("n árboles", m["n_estimators"])

    st.subheader("Importancias")
    top = renombrar_columna_de_variables(
        res.importancias.head(15), "variable", incluir_codigo=True,
    )
    st.dataframe(top, use_container_width=True, hide_index=True)
    fig, ax = plt.subplots(figsize=(8, max(4, len(top) * 0.35)))
    ax.barh(top["variable"][::-1], top["importancia"][::-1], color="#1f4e79")
    ax.set_xlabel("Importancia")
    st.pyplot(fig)
    _boton_descargar(top, "importancias_rf")


# =============================================================================
# SECCIÓN: SHAP
# =============================================================================

def seccion_shap() -> None:
    st.header("🔍 Interpretabilidad con SHAP (XAI)")
    st.markdown(
        "Descompone cada predicción en la contribución de cada variable. "
        "Usa el último modelo entrenado en la sección anterior."
    )

    res_rf = st.session_state.get("res_rf")
    res_arb = st.session_state.get("res_arbol")
    res_log = st.session_state.get("res_logistica")

    opciones = []
    if res_rf:
        opciones.append("Random Forest")
    if res_arb:
        opciones.append("Árbol de decisión")
    if res_log:
        opciones.append("Logística")

    if not opciones:
        st.warning("Primero entrená un modelo en la sección Modelos predictivos.")
        return

    eleccion = st.selectbox("Modelo a explicar", opciones, key="shap_mod")
    n_muestra = st.slider("Filas a explicar (más = más lento)", 100, 2000, 500, step=100, key="shap_n")

    if st.button("Calcular SHAP", type="primary", key="btn_shap"):
        with st.spinner("SHAP en proceso (puede tardar)..."):
            mapa_modelo = {
                "Random Forest": res_rf,
                "Árbol de decisión": res_arb,
                "Logística": res_log,
            }
            res_modelo = mapa_modelo[eleccion]
            modelo = res_modelo.modelo if hasattr(res_modelo, "modelo") else res_modelo.modelo_sklearn
            shap_res = explicar_modelo(
                modelo=modelo,
                X=res_modelo.datos.X_test,
                n_muestra=n_muestra,
            )
            st.session_state["res_shap"] = shap_res

    if "res_shap" in st.session_state:
        shap_res = st.session_state["res_shap"]
        st.subheader("Importancias globales (mean |SHAP|)")
        imp_shap_legible = renombrar_columna_de_variables(
            shap_res.importancias_globales, "variable", incluir_codigo=True,
        )
        st.dataframe(imp_shap_legible.head(15), use_container_width=True, hide_index=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Importancia (barra)**")
            try:
                st.pyplot(importance_bar_objeto(shap_res))
            except Exception as e:
                st.error(f"Error: {e}")
        with col2:
            st.markdown("**Summary plot (beeswarm)**")
            try:
                st.pyplot(summary_plot_objeto(shap_res))
            except Exception as e:
                st.error(f"Error: {e}")

        var_dep = st.selectbox(
            "Variable para dependence plot",
            options=shap_res.X_muestra.columns.tolist(),
            key="shap_dep_var",
            format_func=nombre_completo,
        )
        if var_dep:
            try:
                st.pyplot(dependence_plot_objeto(shap_res, var_dep))
            except Exception as e:
                st.error(f"Error en dependence plot: {e}")


# =============================================================================
# SECCIÓN: CLÚSTERES
# =============================================================================

def seccion_clusters() -> None:
    df = st.session_state["df_trabajado"]

    st.header("🧬 Clústeres y segmentos vulnerables")

    candidatos = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c]) and df[c].nunique(dropna=True) > 1
    ]
    features = st.multiselect(
        "Variables para clusterizar",
        options=candidatos,
        default=[c for c in ["CH06", "NIVEL_ED", "IPCF", "IX_TOT"] if c in candidatos][:5],
        key="clu_feat",
        format_func=nombre_completo,
    )

    metodo = st.radio("Método", ["K-means", "Jerárquico (Ward)"], horizontal=True, key="clu_met")

    if metodo == "K-means":
        c1, c2 = st.columns(2)
        k_min = c1.slider("k mínimo", 2, 5, 2, key="clu_kmin")
        k_max = c2.slider("k máximo", 3, 10, 6, key="clu_kmax")
    else:
        k = st.slider("k (clústeres)", 2, 8, 4, key="clu_k")

    if st.button("Ejecutar clustering", type="primary", key="btn_clu"):
        if len(features) < 2:
            st.error("Elegí al menos 2 variables.")
            return
        with st.spinner("Clusterizando..."):
            if metodo == "K-means":
                res = kmeans_cluster(df, features, k_min=k_min, k_max=k_max)
            else:
                res = jerarquico_cluster(df, features, k=k)
            st.session_state["res_clusters"] = res

    if "res_clusters" in st.session_state:
        res = st.session_state["res_clusters"]
        c1, c2 = st.columns(2)
        c1.metric("k seleccionado", res.k)
        c2.metric("Silueta", res.silhouette)

        if not res.metricas_por_k.empty:
            st.subheader("Métricas por k probado")
            st.dataframe(res.metricas_por_k, use_container_width=True, hide_index=True)

        st.subheader("Distribución por clúster")
        st.dataframe(res.distribucion, use_container_width=True, hide_index=True)

        st.subheader("Perfil de cada clúster (medias)")
        perfil_legible = renombrar_columna_de_variables(
            res.perfil, "variable", incluir_codigo=True,
        )
        st.dataframe(perfil_legible, use_container_width=True, hide_index=True)
        _boton_descargar(perfil_legible, "perfil_clusters")


# =============================================================================
# MAIN
# =============================================================================

def landing() -> None:
    st.title("📊 eph-analyzer")
    st.markdown("""
    Herramienta para el análisis de microdatos de la **Encuesta Permanente de Hogares (EPH)** del INDEC.

    👈 **Empezá subiendo una base** en la barra lateral. Aceptamos:

    - Excel (`.xlsx`, `.xls`)
    - Texto delimitado (`.csv`, `.txt`)
    - Comprimido del INDEC (`.zip`)
    - Parquet (`.parquet`)

    El programa detecta automáticamente si es **base de hogar**, **individuo**, **módulo TIC**, y aplica:

    | Bloque | Métodos |
    |---|---|
    | 📈 Descriptivo | Frecuencias, media, mediana, IC, tablas cruzadas |
    | 📉 Desigualdad | Quintiles, Gini, Theil, comparación regional |
    | 🔗 Correlaciones | Pearson, Kendall, Spearman, Cronbach |
    | 🌐 Exclusión digital | Índice compuesto (3 dimensiones) |
    | 🤖 Predictivo | Logística, Árbol, Random Forest |
    | 🔍 SHAP (XAI) | Summary plot, dependence plot, importancias |
    | 🧬 Clústeres | K-means, jerárquico Ward |

    Toda la metodología sigue **Larrea (2025), UNQ**. Funciona offline en tu computadora o
    desplegada en Streamlit Community Cloud.
    """)


def main() -> None:
    init_state()
    sidebar_carga()

    if st.session_state["df_trabajado"] is None:
        landing()
        return

    secciones = {
        "Vista general": seccion_overview,
        "Estadística descriptiva": seccion_descriptivo,
        "Desigualdad": seccion_desigualdad,
        "Correlaciones": seccion_correlaciones,
        "Índice de exclusión digital": seccion_indice,
        "Modelos predictivos": seccion_modelos,
        "SHAP (XAI)": seccion_shap,
        "Clústeres": seccion_clusters,
    }

    eleccion = st.sidebar.radio(
        "3️⃣ Sección",
        options=list(secciones.keys()),
        key="seccion_actual",
    )
    secciones[eleccion]()


if __name__ == "__main__":
    main()
