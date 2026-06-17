"""Preparación de microdatos: merge hogar-individuo, índices proxy y validación."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import HOGAR_CORE, IND_CORE, IND_TIC, REGIONES


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    if name not in df.columns:
        return pd.Series(np.nan, index=df.index)
    return _num(df[name])


def _yes_no_flag(s: pd.Series) -> pd.Series:
    """Codifica variables binarias EPH/MAUTIC a exclusión (1=excluido, 0=no).

    En MAUTIC (módulo TIC EPH) las variables de acceso del hogar suelen estar codificadas como:
    - 1 = No
    - 2 = Sí
    - 9 = No responde
    """
    if s is None:
        return pd.Series(dtype=float)
    if not isinstance(s, pd.Series):
        s = pd.Series(s)
    v = _num(s)
    out = pd.Series(np.nan, index=s.index, dtype=float)
    out[v == 2] = 0.0  # tiene / sí
    out[v == 1] = 1.0  # no tiene / no
    return out


def _uso_tic_flag(s: pd.Series) -> pd.Series:
    """Codifica variables de uso TIC del individuo a exclusión (1=excluido, 0=no).

    En los microdatos EPH+MAUTIC, las variables de uso suelen venir como:
    - 0 = no usó
    - valores positivos = usó (minutos, frecuencia o similar)
    - -9/9 = no responde / sin dato
    """
    if s is None:
        return pd.Series(dtype=float)
    if not isinstance(s, pd.Series):
        s = pd.Series(s)
    v = _num(s)
    out = pd.Series(np.nan, index=s.index, dtype=float)
    out[v == 0] = 1.0
    out[v > 0] = 0.0
    return out


def _educacion_proxies(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Proxies educativos según NIVEL_ED (EPH) o CH12 categórico."""
    nivel = _col(df, "NIVEL_ED")
    ch12 = _col(df, "CH12")

    if nivel.notna().sum() > len(df) * 0.5:
        # 1..7: primaria incompleta → postgrado
        secundario = (nivel >= 4).astype(float)
        superior = (nivel >= 6).astype(float)
        return secundario, superior

    # CH12 categórico EPH: 4+ secundaria completa, 6+ universitaria
    secundario = ch12.isin([4, 5, 6, 7, 8, 9]).astype(float)
    superior = ch12.isin([6, 7, 8, 9]).astype(float)
    return secundario, superior


def validate_microdata(df: pd.DataFrame) -> dict:
    report = {"filas": len(df)}
    if "CH06" in df.columns:
        edad = _num(df["CH06"])
        bad = ((edad < 0) | (edad > 100)).sum()
        report["edad_fuera_rango"] = int(bad)
    if "ITF" in df.columns:
        report["itf_negativo"] = int((_num(df["ITF"]) < 0).sum())
    crit = [c for c in ["CH12", "ESTADO", "V11_M", "V12_M"] if c in df.columns]
    report["missing_critico_pct"] = round(df[crit].isna().mean().mean() * 100, 2) if crit else 0.0
    return report


def build_analysis_frame(
    hogar: pd.DataFrame,
    individual: pd.DataFrame,
    *,
    edad_min: int = 15,
    aglomerado: int | None = None,
    include_tic: bool = True,
) -> pd.DataFrame:
    hcols = [c for c in HOGAR_CORE if c in hogar.columns]
    ind_cols = IND_CORE + (IND_TIC if include_tic else [])
    icols = [c for c in ind_cols if c in individual.columns]
    for extra in ("anio", "trimestre"):
        if extra in individual.columns and extra not in icols:
            icols.append(extra)
    h = hogar[hcols].drop_duplicates(subset=["CODUSU"])
    i = individual[icols].copy()
    i["CH06"] = _num(i["CH06"])
    i = i[i["CH06"] >= edad_min]

    if aglomerado is not None:
        i = i[_col(i, "AGLOMERADO") == aglomerado]
        codus = set(i["CODUSU"])
        h = h[h["CODUSU"].isin(codus)]

    tic_h = [c for c in h.columns if c.startswith("V") and c not in ("CODUSU",)]
    tic_rename = {c: f"H_{c}" for c in tic_h if c in h.columns}
    h = h.rename(columns=tic_rename)

    df = i.merge(h, on="CODUSU", how="left", suffixes=("", "_hog"))
    if "anio" not in df.columns and "anio" in i.columns:
        df["anio"] = i["anio"]
    if "trimestre" not in df.columns and "trimestre" in i.columns:
        df["trimestre"] = i["trimestre"]

    # --- Dimensión acceso/uso digital (solo cuando hay módulo TIC) ---
    if include_tic:
        df["excl_sin_pc"] = _yes_no_flag(df.get("H_V10"))
        df["excl_sin_internet_hogar"] = _yes_no_flag(df.get("H_V11"))
        df["excl_sin_uso_cel"] = _uso_tic_flag(df.get("V10_M"))
        df["excl_sin_uso_pc"] = _uso_tic_flag(df.get("V11_M"))
        df["excl_sin_uso_internet"] = _uso_tic_flag(df.get("V12_M"))

        acceso_cols = ["excl_sin_pc", "excl_sin_internet_hogar"]
        uso_cols = ["excl_sin_uso_cel", "excl_sin_uso_pc", "excl_sin_uso_internet"]
        all_excl = acceso_cols + uso_cols

        df["idx_acceso"] = df[acceso_cols].mean(axis=1, skipna=True)
        df["idx_uso"] = df[uso_cols].mean(axis=1, skipna=True)
        df["idx_exclusion_digital"] = df[all_excl].mean(axis=1, skipna=True)
        df["exclusion_digital_alta"] = (
            df["idx_exclusion_digital"] >= df["idx_exclusion_digital"].median()
        ).astype(int)
    else:
        for col in (
            "excl_sin_pc",
            "excl_sin_internet_hogar",
            "excl_sin_uso_cel",
            "excl_sin_uso_pc",
            "excl_sin_uso_internet",
            "idx_acceso",
            "idx_uso",
            "idx_exclusion_digital",
        ):
            df[col] = np.nan
        df["exclusion_digital_alta"] = np.nan

    # --- Proxies movilidad social (educación) ---
    df["secundario_completo"], df["superior"] = _educacion_proxies(df)

    estado = _col(df, "ESTADO")
    df["ocupado"] = (estado == 1).astype(float)
    df["desocupado"] = (estado == 2).astype(float)

    cat = _col(df, "CAT_OCUP")
    df["asalariado_registrado"] = cat.isin([3, 4]).astype(float)

    # PP07H: 1=con descuentos jubilatorios, 2=sin descuentos (informal)
    pp07h = _col(df, "PP07H")
    df["informal_proxy"] = np.where(
        df["ocupado"] == 1,
        pp07h.eq(2).astype(float),
        np.nan,
    )

    dec = _col(df, "DECIFR")
    df["decil_ingreso"] = dec
    df["quintil_bajo"] = (dec <= 2).astype(float)
    df["quintil_alto"] = (dec >= 9).astype(float)

    # Score compuesto movilidad ascendente (proxy)
    df["score_movilidad_proxy"] = (
        df["secundario_completo"].fillna(0) * 0.3
        + df["superior"].fillna(0) * 0.2
        + df["ocupado"].fillna(0) * 0.2
        + (1 - df["informal_proxy"].fillna(1)) * 0.15
        + df["quintil_alto"].fillna(0) * 0.15
    )

    # Vulnerabilidad (objetivo alternativo)
    df["vulnerabilidad_social"] = (
        (1 - df["secundario_completo"].fillna(0)) * 0.35
        + df["desocupado"].fillna(0) * 0.25
        + df["quintil_bajo"].fillna(0) * 0.25
        + df["idx_exclusion_digital"].fillna(0) * 0.15
    )
    df["vulnerabilidad_alta"] = (
        df["vulnerabilidad_social"] >= df["vulnerabilidad_social"].median()
    ).astype(int)

    df["sexo_mujer"] = (_col(df, "CH04") == 2).astype(float)
    df["edad"] = df["CH06"]
    if "REGION" in df.columns:
        reg = _col(df, "REGION").map(REGIONES).fillna("Otra")
        df["region_nombre"] = reg

    df["PONDERA"] = _col(df, "PONDERA").fillna(1)

    return df


def weighted_mean(series: pd.Series, weights: pd.Series) -> float:
    m = series.notna() & weights.notna()
    if not m.any():
        return float("nan")
    w = weights[m]
    s = series[m]
    return float(np.average(s, weights=w))
