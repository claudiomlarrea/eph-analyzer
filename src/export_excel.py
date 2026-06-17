"""Utilidades para exportar tablas a Excel con encabezados legibles."""

from __future__ import annotations

import pandas as pd

from .etiquetador import nombre_completo, nombre_variable, renombrar_columna_de_variables

# Encabezados de columnas de tablas de resultados (no son variables EPH)
NOMBRES_COLUMNAS_TABLA: dict[str, str] = {
    "columna": "Código de variable",
    "nombre_legible": "Nombre de la variable",
    "tipo": "Tipo de dato",
    "n_nulos": "Valores nulos (cantidad)",
    "%_nulos": "Valores nulos (%)",
    "n_unicos": "Valores únicos",
    "categoria": "Categoría",
    "n": "Casos (sin ponderar)",
    "%": "Porcentaje (sin ponderar)",
    "n_ponderado": "Casos ponderados",
    "%_ponderado": "Porcentaje ponderado",
    "variable": "Variable",
    "var1": "Variable 1",
    "var2": "Variable 2",
    "var_1": "Variable 1",
    "var_2": "Variable 2",
    "pearson": "Correlación de Pearson",
    "kendall": "Correlación de Kendall",
    "spearman": "Correlación de Spearman",
    "p_valor": "Valor p",
    "p_value": "Valor p",
    "coef": "Coeficiente",
    "coeficiente": "Coeficiente",
    "OR": "Odds ratio",
    "odds_ratio": "Odds ratio",
    "IC95_inf_OR": "IC 95% inferior (OR)",
    "IC95_sup_OR": "IC 95% superior (OR)",
    "significativa_05": "Significativa al 5%",
    "importancia": "Importancia",
    "cluster": "Clúster",
    "pct": "Porcentaje",
    "grupo": "Grupo",
    "limite_inf": "Límite inferior",
    "limite_sup": "Límite superior",
    "media": "Media",
    "mediana": "Mediana",
    "nivel": "Nivel de exclusión",
    "count": "Cantidad de casos",
    "mean": "Promedio",
    "silhouette": "Coeficiente de silueta",
    "k": "Cantidad de clústeres",
    "alpha": "Alfa de Cronbach",
    "interpretacion": "Interpretación",
    "alpha_sin_item": "Alfa sin el ítem",
    "titulo": "Título del informe",
    "ambito": "Ámbito geográfico",
    "periodo": "Período analizado",
    "registros": "Cantidad de registros",
    "validacion": "Validación de microdatos",
    "fuente": "Fuente de datos",
    "modulo": "Módulo EPH",
    "analisis": "Análisis incluidos",
    "generado": "Fecha de generación",
}

_COLUMNAS_CON_CODIGOS_VARIABLE = frozenset(
    {"variable", "var1", "var2", "var_1", "var_2", "columna"}
)


def _nombre_encabezado(col: str, *, incluir_codigo: bool) -> str:
    c = str(col).strip()
    cu = c.upper()
    if c in NOMBRES_COLUMNAS_TABLA:
        return NOMBRES_COLUMNAS_TABLA[c]
    if cu in NOMBRES_COLUMNAS_TABLA:
        return NOMBRES_COLUMNAS_TABLA[cu]
    fn = nombre_completo if incluir_codigo else nombre_variable
    legible = fn(c)
    if legible != c:
        return legible
    return c.replace("_", " ").capitalize()


def preparar_df_para_excel(
    df: pd.DataFrame,
    *,
    incluir_codigo: bool = True,
) -> pd.DataFrame:
    """Devuelve una copia del DataFrame con encabezados y códigos de variable legibles."""
    if df is None or df.empty:
        return df

    out = df.copy()

    for col in _COLUMNAS_CON_CODIGOS_VARIABLE:
        if col in out.columns:
            out = renombrar_columna_de_variables(out, col, incluir_codigo=incluir_codigo)

    out.columns = [_nombre_encabezado(c, incluir_codigo=incluir_codigo) for c in out.columns]
    return out


def preparar_metadatos_para_excel(meta: dict) -> pd.DataFrame:
    """Convierte metadatos del análisis a una fila con etiquetas legibles."""
    fila = {}
    for clave, valor in meta.items():
        etiqueta = NOMBRES_COLUMNAS_TABLA.get(clave, clave.replace("_", " ").capitalize())
        if isinstance(valor, (dict, list)):
            fila[etiqueta] = str(valor)
        else:
            fila[etiqueta] = valor
    return pd.DataFrame([fila])
