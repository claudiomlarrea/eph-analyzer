"""
Correlaciones y consistencia interna.

Implementa:
    - matriz de correlación de Pearson (lineal, paramétrica)
    - matriz de correlación de Kendall (rangos, no paramétrica)
    - matriz de correlación de Spearman (rangos, no paramétrica)
    - alfa de Cronbach (consistencia interna de una escala/índice)

Las funciones devuelven DataFrames listos para mostrar o exportar.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from scipy import stats


def matriz_correlacion(
    df: pd.DataFrame,
    columnas: Iterable[str] | None = None,
    metodo: str = "pearson",
) -> pd.DataFrame:
    """
    Matriz de correlación entre variables numéricas.

    Parámetros
    ----------
    metodo : 'pearson' | 'kendall' | 'spearman'
    """
    if columnas is None:
        columnas = df.select_dtypes(include=[np.number]).columns.tolist()
    columnas = [c for c in columnas if c in df.columns]
    if not columnas:
        raise ValueError("No hay columnas numéricas válidas.")

    return df[columnas].corr(method=metodo).round(4)


def correlaciones_con_p(
    df: pd.DataFrame,
    columnas: Iterable[str],
    metodo: str = "pearson",
) -> pd.DataFrame:
    """
    Pares de correlaciones con valor p, ordenadas por |r| descendente.

    Útil para reportar correlaciones significativas.
    """
    columnas = [c for c in columnas if c in df.columns]
    sub = df[columnas].apply(pd.to_numeric, errors="coerce").dropna()

    funcs = {
        "pearson": stats.pearsonr,
        "kendall": stats.kendalltau,
        "spearman": stats.spearmanr,
    }
    if metodo not in funcs:
        raise ValueError(f"Método '{metodo}' no soportado.")
    fn = funcs[metodo]

    filas = []
    for i, c1 in enumerate(columnas):
        for c2 in columnas[i + 1:]:
            try:
                r, p = fn(sub[c1], sub[c2])
            except Exception:
                continue
            filas.append({
                "var_1": c1,
                "var_2": c2,
                "r": round(float(r), 4),
                "p_valor": round(float(p), 4),
                "n": int(len(sub)),
                "significativa_05": bool(p < 0.05),
            })
    return (
        pd.DataFrame(filas)
        .sort_values("r", key=lambda s: s.abs(), ascending=False)
        .reset_index(drop=True)
    )


def cronbach_alpha(
    df: pd.DataFrame,
    items: Iterable[str],
    devolver_diagnostico: bool = True,
) -> dict | float:
    """
    Coeficiente alfa de Cronbach para una escala/índice de varios ítems.

    α = (k / (k-1)) * (1 - Σ var(item_i) / var(total))

    Parámetros
    ----------
    items : Iterable[str]
        Lista de columnas que componen la escala (todas numéricas).
    devolver_diagnostico : bool
        Si True devuelve dict con n, k, alpha, alpha_si_quito_item.
        Si False devuelve solo el float.

    Interpretación habitual:
        α >= 0.90  excelente
        0.80–0.89  buena
        0.70–0.79  aceptable
        < 0.70     baja consistencia
    """
    items = [c for c in items if c in df.columns]
    if len(items) < 2:
        raise ValueError("Cronbach requiere al menos 2 ítems.")

    sub = df[items].apply(pd.to_numeric, errors="coerce").dropna()
    if len(sub) < 2:
        raise ValueError("No hay filas válidas en común para los ítems.")

    k = len(items)
    var_items = sub.var(axis=0, ddof=1).sum()
    var_total = sub.sum(axis=1).var(ddof=1)
    if var_total == 0:
        return float("nan") if not devolver_diagnostico else {
            "alpha": float("nan"), "k": k, "n": len(sub),
            "comentario": "Varianza total cero; revisar datos.",
        }
    alpha = (k / (k - 1)) * (1 - var_items / var_total)

    if not devolver_diagnostico:
        return round(float(alpha), 4)

    diag_alpha_si_quito = {}
    for item in items:
        restantes = [c for c in items if c != item]
        if len(restantes) < 2:
            continue
        sub_r = sub[restantes]
        kr = len(restantes)
        v_i = sub_r.var(axis=0, ddof=1).sum()
        v_t = sub_r.sum(axis=1).var(ddof=1)
        if v_t > 0:
            a = (kr / (kr - 1)) * (1 - v_i / v_t)
            diag_alpha_si_quito[item] = round(float(a), 4)

    return {
        "alpha": round(float(alpha), 4),
        "k": int(k),
        "n": int(len(sub)),
        "items": list(items),
        "alpha_si_quito_item": diag_alpha_si_quito,
        "interpretacion": _interpretar_alpha(alpha),
    }


def _interpretar_alpha(a: float) -> str:
    if np.isnan(a):
        return "no calculable"
    if a >= 0.90:
        return "excelente"
    if a >= 0.80:
        return "buena"
    if a >= 0.70:
        return "aceptable"
    if a >= 0.60:
        return "cuestionable"
    return "baja consistencia"
