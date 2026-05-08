"""
Métricas de desigualdad de ingresos para la EPH.

Implementa:
    - quintiles / deciles ponderados con sus límites y media de cada grupo
    - coeficiente de Gini ponderado
    - índice de Theil (T y L) ponderado
    - razón inter-quintil (Q5/Q1)
    - comparación regional (RMBA, NOA, NEA, Cuyo, Pampeana, Patagonia)

Referencias:
    Cowell, F. A. (2011). Measuring Inequality. Oxford University Press.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

PONDERADOR_DEFAULT = "PONDIH"


def _serie_y_pesos(
    df: pd.DataFrame, columna: str, ponderador: str | None
) -> tuple[np.ndarray, np.ndarray]:
    """Extrae la serie y los pesos limpios y alineados."""
    if columna not in df.columns:
        raise KeyError(f"Columna '{columna}' no está en el DataFrame.")

    s = pd.to_numeric(df[columna], errors="coerce")
    if ponderador and ponderador in df.columns:
        w = pd.to_numeric(df[ponderador], errors="coerce")
    else:
        w = pd.Series(np.ones(len(s)), index=s.index)

    mask = s.notna() & (s >= 0) & w.notna() & (w > 0)
    return s[mask].values.astype(float), w[mask].values.astype(float)


def quintiles(
    df: pd.DataFrame,
    columna_ingreso: str = "IPCF",
    ponderador: str | None = PONDERADOR_DEFAULT,
    n_grupos: int = 5,
) -> pd.DataFrame:
    """
    Calcula los quintiles (o deciles si n_grupos=10) ponderados.

    Devuelve un DataFrame con: grupo, limite_inf, limite_sup, n_ponderado,
    media, mediana, % del ingreso total.
    """
    s, w = _serie_y_pesos(df, columna_ingreso, ponderador)

    orden = np.argsort(s)
    s_o, w_o = s[orden], w[orden]

    cum_w = np.cumsum(w_o)
    cum_w_norm = cum_w / cum_w[-1]
    limites_pct = np.linspace(0, 1, n_grupos + 1)

    grupos = np.searchsorted(cum_w_norm, limites_pct[1:], side="right")
    grupos = np.clip(grupos, 1, len(s_o))

    nombres = [f"Q{i+1}" for i in range(n_grupos)]
    if n_grupos == 10:
        nombres = [f"D{i+1}" for i in range(n_grupos)]

    filas = []
    inicio = 0
    total_ingreso = float((s * w).sum())
    for i, fin in enumerate(grupos):
        s_g, w_g = s_o[inicio:fin], w_o[inicio:fin]
        if len(s_g) == 0:
            continue
        ingreso_g = float((s_g * w_g).sum())
        filas.append({
            "grupo": nombres[i],
            "limite_inf": round(float(s_g[0]), 2),
            "limite_sup": round(float(s_g[-1]), 2),
            "n_ponderado": int(round(w_g.sum())),
            "media": round(float(np.average(s_g, weights=w_g)), 2),
            "mediana": round(float(_mediana_pesada(s_g, w_g)), 2),
            "%_ingreso_total": round(100 * ingreso_g / total_ingreso, 2),
        })
        inicio = fin

    return pd.DataFrame(filas)


def _mediana_pesada(valores: np.ndarray, pesos: np.ndarray) -> float:
    """Mediana ponderada (interpola entre los valores más cercanos al 0.5)."""
    orden = np.argsort(valores)
    v_o, w_o = valores[orden], pesos[orden]
    cum = np.cumsum(w_o)
    if cum[-1] == 0:
        return float("nan")
    return float(v_o[np.searchsorted(cum, cum[-1] / 2)])


def gini(
    df: pd.DataFrame,
    columna_ingreso: str = "IPCF",
    ponderador: str | None = PONDERADOR_DEFAULT,
) -> float:
    """
    Coeficiente de Gini ponderado.

    Fórmula:
        G = 1 - 2 * Σ (w_i * F_i * y_i) / (μ * Σ w_i * F_i)
    donde F_i es la posición acumulada y_i, ordenada por y_i ascendente.
    Resultado en [0, 1]: 0 = igualdad perfecta, 1 = desigualdad máxima.
    """
    y, w = _serie_y_pesos(df, columna_ingreso, ponderador)
    if len(y) < 2:
        return float("nan")

    orden = np.argsort(y)
    y_o, w_o = y[orden], w[orden]

    sw = w_o.sum()
    swyx = (w_o * (np.cumsum(w_o) - 0.5 * w_o) * y_o).sum()
    swy = (w_o * y_o).sum()
    if swy == 0:
        return float("nan")

    g = (2.0 * swyx) / (sw * swy) - (1.0 - 1.0 / sw)
    return float(round(g, 4))


def theil(
    df: pd.DataFrame,
    columna_ingreso: str = "IPCF",
    ponderador: str | None = PONDERADOR_DEFAULT,
) -> dict:
    """
    Índices de Theil T (sensible a la cima) y L (sensible a la base).
    """
    y, w = _serie_y_pesos(df, columna_ingreso, ponderador)
    if len(y) < 2:
        return {"theil_T": float("nan"), "theil_L": float("nan")}

    mu = float(np.average(y, weights=w))
    if mu <= 0:
        return {"theil_T": float("nan"), "theil_L": float("nan")}

    yp = y / mu
    sw = w.sum()
    yp_pos = yp[yp > 0]
    w_pos = w[yp > 0]

    T = float(np.sum(w_pos * yp_pos * np.log(yp_pos)) / sw)
    L = float(np.sum(w_pos * np.log(1.0 / yp_pos)) / sw) if (yp_pos > 0).all() else np.nan

    return {"theil_T": round(T, 4), "theil_L": round(L, 4)}


def razon_quintil(
    df: pd.DataFrame,
    columna_ingreso: str = "IPCF",
    ponderador: str | None = PONDERADOR_DEFAULT,
) -> float:
    """Razón entre la media del Q5 y la del Q1."""
    q = quintiles(df, columna_ingreso, ponderador, n_grupos=5)
    if q.empty:
        return float("nan")
    media_q5 = q.loc[q["grupo"] == "Q5", "media"].iloc[0]
    media_q1 = q.loc[q["grupo"] == "Q1", "media"].iloc[0]
    return round(float(media_q5 / media_q1), 2) if media_q1 > 0 else float("nan")


def comparar_por_grupo(
    df: pd.DataFrame,
    columna_ingreso: str = "IPCF",
    columna_grupo: str = "REGION",
    ponderador: str | None = PONDERADOR_DEFAULT,
) -> pd.DataFrame:
    """
    Comparación regional (o por cualquier grupo): media, mediana, Gini, n.
    """
    if columna_grupo not in df.columns:
        raise KeyError(f"Columna '{columna_grupo}' no encontrada.")

    filas = []
    for grupo, g in df.groupby(columna_grupo, dropna=False):
        if len(g) == 0:
            continue
        try:
            y, w = _serie_y_pesos(g, columna_ingreso, ponderador)
        except KeyError:
            continue
        if len(y) == 0:
            continue
        filas.append({
            "grupo": grupo,
            "n_ponderado": int(round(w.sum())),
            "media": round(float(np.average(y, weights=w)), 2),
            "mediana": round(float(_mediana_pesada(y, w)), 2),
            "gini": gini(g, columna_ingreso, ponderador),
        })
    out = pd.DataFrame(filas).sort_values("media", ascending=False).reset_index(drop=True)
    return out
