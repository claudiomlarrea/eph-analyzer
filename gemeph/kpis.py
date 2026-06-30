"""Indicadores agregados del gemelo territorial."""

from __future__ import annotations

import numpy as np
import pandas as pd

from indec_auto.src.prepare import weighted_mean

from .config import MIN_N_ADVERTENCIA, MIN_N_INDIVIDUOS


def _wmean(df: pd.DataFrame, col: str) -> float | None:
    if col not in df.columns or not df[col].notna().any():
        return None
    w = df.get("PONDERA", pd.Series(1.0, index=df.index))
    val = weighted_mean(df[col], w)
    return None if np.isnan(val) else round(float(val), 4)


def _pct(df: pd.DataFrame, col: str) -> float | None:
    v = _wmean(df, col)
    return None if v is None else round(v * 100, 2)


def compute_kpis(df: pd.DataFrame, *, include_tic: bool = True) -> dict:
    """Calcula KPIs ponderados para un subconjunto del panel."""
    n = len(df)
    peso = df["PONDERA"].sum() if "PONDERA" in df.columns else float(n)

    kpis: dict = {
        "n_individuos": int(n),
        "peso_expansion": round(float(peso), 1),
        "muestra_suficiente": n >= MIN_N_INDIVIDUOS,
        "muestra_advertencia": n < MIN_N_ADVERTENCIA,
    }

    for key, col in (
        ("pct_secundario_completo", "secundario_completo"),
        ("pct_superior", "superior"),
        ("pct_ocupado", "ocupado"),
        ("score_movilidad_proxy", "score_movilidad_proxy"),
        ("vulnerabilidad_social", "vulnerabilidad_social"),
    ):
        val = _pct(df, col) if key.startswith("pct_") else _wmean(df, col)
        if val is not None:
            kpis[key] = val

    # Informalidad entre ocupados
    if "ocupado" in df.columns and (df["ocupado"] == 1).any():
        occ = df.loc[df["ocupado"] == 1]
        inf = _pct(occ, "informal_proxy")
        if inf is not None:
            kpis["pct_informal_ocupados"] = inf

    if include_tic and "idx_exclusion_digital" in df.columns and df["idx_exclusion_digital"].notna().any():
        kpis["idx_exclusion_digital"] = _wmean(df, "idx_exclusion_digital")
        alta = _pct(df, "exclusion_digital_alta")
        if alta is not None:
            kpis["pct_exclusion_digital_alta"] = alta

    brechas = _brechas(df, include_tic=include_tic)
    if brechas:
        kpis["brechas"] = brechas

    return kpis


def _brechas(df: pd.DataFrame, *, include_tic: bool) -> dict:
    out: dict = {}
    if "CH04" in df.columns and "ocupado" in df.columns:
        sexo = pd.to_numeric(df["CH04"], errors="coerce")
        muj = df.loc[sexo == 2]
        hom = df.loc[sexo == 1]
        if len(muj) >= 30 and len(hom) >= 30:
            pm = _pct(muj, "ocupado")
            ph = _pct(hom, "ocupado")
            if pm is not None and ph is not None:
                out["ocupacion_mujer_menos_hombre_pp"] = round(pm - ph, 2)

    if include_tic and "excl_sin_internet_hogar" in df.columns and "decil_ingreso" in df.columns:
        dec = pd.to_numeric(df["decil_ingreso"], errors="coerce")
        q1 = df.loc[dec <= 2]
        q5 = df.loc[dec >= 9]
        if len(q1) >= 20 and len(q5) >= 20:
            e1 = _pct(q1, "excl_sin_internet_hogar")
            e5 = _pct(q5, "excl_sin_internet_hogar")
            if e1 is not None and e5 is not None:
                out["internet_q1_menos_q5_pp"] = round(e1 - e5, 2)

    return out


def compute_evolution(df: pd.DataFrame, *, include_tic: bool = True) -> list[dict]:
    """Serie anual de KPIs para un territorio."""
    if "anio" not in df.columns:
        return []
    rows = []
    for anio, g in df.groupby("anio"):
        row = {"anio": int(anio), **compute_kpis(g, include_tic=include_tic)}
        rows.append(row)
    return sorted(rows, key=lambda r: r["anio"])
