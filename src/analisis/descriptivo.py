"""
Estadística descriptiva ponderada para la EPH.

La EPH es una encuesta con muestreo complejo. Para que las estadísticas
sean representativas de la población urbana hay que **ponderar** por la
columna `PONDERA` (factor de expansión). Estas funciones lo hacen por
defecto si la columna está disponible.

Funciones principales:
    - `frecuencias`: tabla de frecuencias absolutas y relativas.
    - `estadisticos`: media, mediana, desvío, IC95, cuantiles, n.
    - `tabla_cruzada`: cruzamiento entre dos variables, ponderado.
    - `resumen_general`: estadísticos globales del DataFrame.

Todas devuelven un `pandas.DataFrame` listo para mostrar o exportar.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from statsmodels.stats.weightstats import DescrStatsW

PONDERADOR_DEFAULT = "PONDERA"


def _resolver_pesos(df: pd.DataFrame, ponderador: str | None) -> pd.Series | None:
    """Devuelve la serie de pesos a usar, o None si no hay/no se desea."""
    if ponderador is None:
        return None
    if ponderador not in df.columns:
        return None
    pesos = pd.to_numeric(df[ponderador], errors="coerce").fillna(0)
    if pesos.sum() <= 0:
        return None
    return pesos


def frecuencias(
    df: pd.DataFrame,
    columna: str,
    ponderador: str | None = PONDERADOR_DEFAULT,
    incluir_nulos: bool = True,
    ordenar_por: str = "frecuencia",
) -> pd.DataFrame:
    """
    Tabla de frecuencias absolutas y relativas, ponderada cuando es posible.

    Parámetros
    ----------
    df : DataFrame
    columna : str
        Variable a tabular (puede ser categórica o numérica discreta).
    ponderador : str | None
        Nombre del peso. Default: 'PONDERA'. Si la columna no existe,
        se calculan frecuencias sin ponderar.
    incluir_nulos : bool
        Si True, agrega una fila para los NaN.
    ordenar_por : 'frecuencia' | 'categoria'
        Cómo ordenar la tabla resultante.

    Returns
    -------
    DataFrame con columnas: categoria, n, %, n_ponderado, %_ponderado.
    """
    if columna not in df.columns:
        raise KeyError(f"Columna '{columna}' no encontrada en el DataFrame.")

    s = df[columna]
    pesos = _resolver_pesos(df, ponderador)

    if incluir_nulos:
        s_norm = s.fillna("__NULO__")
    else:
        mask = s.notna()
        s_norm = s[mask]
        if pesos is not None:
            pesos = pesos[mask]

    n_simple = s_norm.value_counts(dropna=False)
    pct_simple = (n_simple / n_simple.sum() * 100).round(2)

    salida = pd.DataFrame({
        "categoria": n_simple.index.astype(str).str.replace("__NULO__", "(NaN)"),
        "n": n_simple.values,
        "%": pct_simple.values,
    })

    if pesos is not None:
        agg = (
            pd.DataFrame({"_v": s_norm, "_w": pesos})
            .groupby("_v", dropna=False)["_w"]
            .sum()
        )
        agg_total = agg.sum()
        agg_pct = (agg / agg_total * 100).round(2)
        n_pond = salida["categoria"].str.replace("(NaN)", "__NULO__", regex=False).map(
            agg.rename(index=lambda x: str(x))
        )
        pct_pond = salida["categoria"].str.replace("(NaN)", "__NULO__", regex=False).map(
            agg_pct.rename(index=lambda x: str(x))
        )
        salida["n_ponderado"] = n_pond.round(0).astype("Int64")
        salida["%_ponderado"] = pct_pond.round(2)

    if ordenar_por == "frecuencia":
        salida = salida.sort_values("n", ascending=False).reset_index(drop=True)
    else:
        salida = salida.sort_values("categoria").reset_index(drop=True)

    return salida


def estadisticos(
    df: pd.DataFrame,
    columna: str,
    ponderador: str | None = PONDERADOR_DEFAULT,
    cuantiles: Iterable[float] = (0.25, 0.5, 0.75),
) -> pd.Series:
    """
    Resumen estadístico de una variable numérica, ponderado.

    Devuelve: n, n_validos, missing, media, desvio, ic95_inf, ic95_sup,
    min, max, cuantiles solicitados.
    """
    if columna not in df.columns:
        raise KeyError(f"Columna '{columna}' no encontrada en el DataFrame.")

    s_raw = pd.to_numeric(df[columna], errors="coerce")
    pesos = _resolver_pesos(df, ponderador)

    mask = s_raw.notna()
    s = s_raw[mask]
    n_total = len(s_raw)
    n_validos = int(mask.sum())
    n_missing = n_total - n_validos

    if n_validos == 0:
        return pd.Series(
            {
                "n": n_total,
                "n_validos": 0,
                "missing": n_missing,
                "media": np.nan,
                "mediana": np.nan,
                "desvio": np.nan,
                "ic95_inf": np.nan,
                "ic95_sup": np.nan,
                "min": np.nan,
                "max": np.nan,
            },
            name=columna,
        )

    if pesos is not None:
        w = pesos[mask].astype(float).values
        ds = DescrStatsW(s.values, weights=w, ddof=1)
        media = ds.mean
        desvio = ds.std
        try:
            ic_inf, ic_sup = ds.tconfint_mean(alpha=0.05)
        except Exception:
            ic_inf, ic_sup = (np.nan, np.nan)
        cuantiles_vals = ds.quantile(np.array(list(cuantiles)), return_pandas=False)
        mediana = float(ds.quantile(np.array([0.5]), return_pandas=False)[0])
    else:
        media = float(s.mean())
        desvio = float(s.std(ddof=1))
        sem = desvio / np.sqrt(n_validos) if n_validos > 1 else np.nan
        ic_inf = media - 1.96 * sem if not np.isnan(sem) else np.nan
        ic_sup = media + 1.96 * sem if not np.isnan(sem) else np.nan
        cuantiles_vals = s.quantile(list(cuantiles)).values
        mediana = float(s.median())

    out: dict[str, float | int] = {
        "n": n_total,
        "n_validos": n_validos,
        "missing": n_missing,
        "media": round(float(media), 4),
        "mediana": round(float(mediana), 4),
        "desvio": round(float(desvio), 4),
        "ic95_inf": round(float(ic_inf), 4) if not np.isnan(ic_inf) else np.nan,
        "ic95_sup": round(float(ic_sup), 4) if not np.isnan(ic_sup) else np.nan,
        "min": float(s.min()),
        "max": float(s.max()),
    }
    for q, v in zip(cuantiles, cuantiles_vals):
        out[f"q{int(q*100)}"] = round(float(v), 4)

    return pd.Series(out, name=columna)


def tabla_cruzada(
    df: pd.DataFrame,
    fila: str,
    columna: str,
    ponderador: str | None = PONDERADOR_DEFAULT,
    normalizar: str | None = "fila",
) -> pd.DataFrame:
    """
    Tabla cruzada (cross-tab) ponderada.

    `normalizar` ∈ {None, 'fila', 'columna', 'total'}.
    """
    if fila not in df.columns or columna not in df.columns:
        raise KeyError(f"Columnas '{fila}' o '{columna}' no encontradas.")

    pesos = _resolver_pesos(df, ponderador)

    norm_arg = {
        None: False,
        "fila": "index",
        "columna": "columns",
        "total": "all",
    }[normalizar]

    if pesos is not None:
        tab = pd.crosstab(
            df[fila], df[columna],
            values=pesos, aggfunc="sum",
            normalize=norm_arg, dropna=False,
        )
    else:
        tab = pd.crosstab(df[fila], df[columna], normalize=norm_arg, dropna=False)

    if normalizar is not None:
        tab = (tab * 100).round(2)
    return tab


def resumen_general(
    df: pd.DataFrame,
    columnas_numericas: Iterable[str] | None = None,
    ponderador: str | None = PONDERADOR_DEFAULT,
) -> pd.DataFrame:
    """
    Tabla resumen para todas (o algunas) variables numéricas del DataFrame.
    """
    if columnas_numericas is None:
        columnas_numericas = df.select_dtypes(include=[np.number]).columns.tolist()
        ignorar = {"CODUSU", "NRO_HOGAR", "COMPONENTE", ponderador or ""}
        columnas_numericas = [c for c in columnas_numericas if c not in ignorar]

    filas = []
    for col in columnas_numericas:
        try:
            filas.append(estadisticos(df, col, ponderador=ponderador))
        except Exception:
            continue
    return pd.DataFrame(filas)
